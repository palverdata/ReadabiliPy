/*
 * This file is part of ReadabiliPy
 */

const fs = require("fs");
const { Readability } = require("@mozilla/readability");
const { JSDOM } = require("jsdom");

function readFile(filePath) {
  return fs.readFileSync(filePath, { encoding: "utf-8" }).trim();
}

function writeFile(data, filePath) {
  return fs.writeFileSync(filePath, data, { encoding: "utf-8" });
}

function now() {
  return new Date().toISOString();
}

function main() {
  let outFilePath;

  const argv = require("minimist")(process.argv.slice(2));
  if (argv["i"] === undefined) {
    console.log("Input file required.");
    return 1;
  }

  const inFilePath = argv["i"];
  if (typeof argv["o"] !== "undefined") {
    outFilePath = argv["o"];
  } else {
    outFilePath = inFilePath + ".simple.json";
  }

  const html = readFile(inFilePath);
  console.log(`[${now()}] Read ${html.length} characters from ${inFilePath}`);
  const doc = new JSDOM(html);
  console.log(`[${now()}] Creating readability object...`);
  const reader = new Readability(doc.window.document);
  console.log(`[${now()}] Parsing article...`);
  const article = reader.parse();
  console.log(`[${now()}] Article parsed with title: ${article.title}`);
  console.log(`[${now()}] Writing article to ${outFilePath}...`);

  writeFile(JSON.stringify(article), outFilePath);
  return 0;
}

main();
