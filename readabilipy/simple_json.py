import hashlib
import json
import os
import tempfile
import subprocess
import sys

from bs4 import BeautifulSoup
from bs4.element import Comment, NavigableString, CData
from .simple_tree import simple_tree_from_html_string
from .extractors import extract_date, extract_title
from .simplifiers import normalise_text
from .utils import run_npm_install
from .models.ReadableArticle import ReadableArticle


def have_node():
    """Check that we can run node and have a new enough version """
    try:
        cp = subprocess.run(['node', '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    except FileNotFoundError:
        return False

    if not cp.returncode == 0:
        return False

    major = int(cp.stdout.split(b'.')[0].lstrip(b'v'))
    if major < 10:
        return False

    # check that this package has a node_modules dir in the javascript
    # directory, if it doesn't, it wasn't installed with Node support
    jsdir = os.path.join(os.path.dirname(__file__), 'javascript')
    node_modules = os.path.join(jsdir, 'node_modules')
    if not os.path.exists(node_modules):
        # Try installing node dependencies.
        run_npm_install()
    return os.path.exists(node_modules)



def simple_json_from_html_string(html, content_digests=False, node_indexes=False, use_readability=True) -> ReadableArticle:
    if use_readability and not have_node():
        print(
            "Warning: node executable not found, reverting to pure-Python mode. "
            "Install Node.js v10 or newer to use Readability.js.",
            file=sys.stderr,
        )
        use_readability = False

    input_json = {}

    if use_readability:
        # Write input HTML to a temporary file for the Node.js script
        with tempfile.NamedTemporaryFile(delete=False, mode="w+", encoding="utf-8", prefix="readabilipy") as f_html:
            f_html.write(html)
            html_path = f_html.name

        json_path = html_path + ".json"
        jsdir = os.path.join(os.path.dirname(__file__), "javascript")

        try:
            # Call Mozilla's Readability.js via Node.js
            subprocess.run(
                ["node", "ExtractArticle.js", "-i", html_path, "-o", json_path],
                cwd=jsdir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )

            # Read the output JSON
            with open(json_path, "r", encoding="utf-8") as json_file:
                input_json = json.load(json_file)

        except subprocess.CalledProcessError as e:
            print(f"Error calling Node.js script: {e.stderr}", file=sys.stderr)
            raise
        finally:
            # Clean up temporary files
            if os.path.exists(json_path):
                os.unlink(json_path)
            if os.path.exists(html_path):
                os.unlink(html_path)

    else:
        # Fallback: Pure-Python mode
        input_json = {
            "title": extract_title(html),
            "publishedTime": extract_date(html),
            "content": str(simple_tree_from_html_string(html)),
        }

    # Populate and return the ReadableArticle dataclass
    return ReadableArticle(
        title=input_json.get("title"),
        byline=input_json.get("byline"),
        dir=input_json.get("dir"),
        lang=input_json.get("lang"),
        content=input_json.get("content"),
        text_content=plain_content(input_json.get("content", ""), content_digests, node_indexes)
        if "content" in input_json
        else None,
        length=len(input_json.get("content", "")) if input_json.get("content") else None,
        excerpt=input_json.get("excerpt"),
        site_name=input_json.get("siteName"),
        published_time=input_json.get("publishedTime"),
    )



def extract_text_blocks_js(paragraph_html):
    # Load article as DOM
    soup = BeautifulSoup(paragraph_html, 'html.parser')
    # Select all text blocks
    text_blocks = [{"text": str(s)} for s in soup.find_all(string=True)]
    return text_blocks


def extract_text_blocks_as_plain_text(paragraph_html):
    # Load article as DOM
    soup = BeautifulSoup(paragraph_html, 'html.parser')
    # Select all lists
    list_elements = soup.find_all(['ul', 'ol'])
    # Prefix text in all list items with "* " and make lists paragraphs
    for list_element in list_elements:
        plain_items = "".join(list(filter(None, [plain_text_leaf_node(li)["text"] for li in list_element.find_all('li')])))
        list_element.string = plain_items
        list_element.name = "p"
    # Select all text blocks
    text_blocks = [s.parent for s in soup.find_all(string=True)]
    text_blocks = [plain_text_leaf_node(block) for block in text_blocks]
    # Drop empty paragraphs
    text_blocks = list(filter(lambda p: p["text"] is not None, text_blocks))
    return text_blocks


def plain_text_leaf_node(element):
    # Extract all text, stripped of any child HTML elements and normalise it
    plain_text = normalise_text(element.get_text())
    if plain_text != "" and element.name == "li":
        plain_text = f"* {plain_text}, "
    if plain_text == "":
        plain_text = None
    if "data-node-index" in element.attrs:
        plain = {"node_index": element["data-node-index"], "text": plain_text}
    else:
        plain = {"text": plain_text}
    return plain


def plain_content(readability_content, content_digests, node_indexes):
    # Load article as DOM
    soup = BeautifulSoup(readability_content, 'html.parser')
    # Make all elements plain
    elements = plain_elements(soup.contents, content_digests, node_indexes)
    if node_indexes:
        # Add node index attributes to nodes
        elements = [add_node_indexes(element) for element in elements]
    # Replace article contents with plain elements
    soup.contents = elements
    return str(soup)


def plain_elements(elements, content_digests, node_indexes):
    # Get plain content versions of all elements
    elements = [plain_element(element, content_digests, node_indexes)
                for element in elements]
    if content_digests:
        # Add content digest attribute to nodes
        elements = [add_content_digest(element) for element in elements]
    return elements


def plain_element(element, content_digests, node_indexes):
    # For lists, we make each item plain text
    if is_leaf(element):
        # For leaf node elements, extract the text content, discarding any HTML tags
        # 1. Get element contents as text
        plain_text = element.get_text()
        # 2. Normalise the extracted text string to a canonical representation
        plain_text = normalise_text(plain_text)
        # 3. Update element content to be plain text
        element.string = plain_text
    elif is_text(element):
        if is_non_printing(element):
            # The simplified HTML may have come from Readability.js so might
            # have non-printing text (e.g. Comment or CData). In this case, we
            # keep the structure, but ensure that the string is empty.
            element = type(element)("")
        else:
            plain_text = element.string
            plain_text = normalise_text(plain_text)
            element = type(element)(plain_text)
    else:
        # If not a leaf node or leaf type call recursively on child nodes, replacing
        element.contents = plain_elements(element.contents, content_digests, node_indexes)
    return element


def is_leaf(element):
    return (element.name in ['p', 'li'])


def is_text(element):
    return isinstance(element, NavigableString)


def is_non_printing(element):
    return any(isinstance(element, _e) for _e in [Comment, CData])


def add_node_indexes(element, node_index="0"):
    # Can't add attributes to string types
    if is_text(element):
        return element
    # Add index to current element
    element["data-node-index"] = node_index
    # Add index to child elements
    for local_idx, child in enumerate(
            [c for c in element.contents if not is_text(c)], start=1):
        # Can't add attributes to leaf string types
        child_index = f"{node_index}.{local_idx}"
        add_node_indexes(child, node_index=child_index)
    return element


def add_content_digest(element):
    if not is_text(element):
        element["data-content-digest"] = content_digest(element)
    return element


def content_digest(element):
    if is_text(element):
        # Hash
        trimmed_string = element.string.strip()
        if trimmed_string == "":
            digest = ""
        else:
            digest = hashlib.sha256(trimmed_string.encode('utf-8')).hexdigest()
    else:
        contents = element.contents
        num_contents = len(contents)
        if num_contents == 0:
            # No hash when no child elements exist
            digest = ""
        elif num_contents == 1:
            # If single child, use digest of child
            digest = content_digest(contents[0])
        else:
            # Build content digest from the "non-empty" digests of child nodes
            digest = hashlib.sha256()
            child_digests = list(
                filter(lambda x: x != "", [content_digest(content) for content in contents]))
            for child in child_digests:
                digest.update(child.encode('utf-8'))
            digest = digest.hexdigest()
    return digest
