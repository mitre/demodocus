const fs = require('fs');

let crawlDirs = [];
fs.readdirSync('./public/crawls').forEach(file => {
  crawlDirs.push(file);
});

process.env.VUE_APP_CRAWL_FOLDERS = JSON.stringify(crawlDirs);