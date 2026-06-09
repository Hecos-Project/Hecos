const marked = require('./hecos/modules/web_ui/static/vendor/marked.min.js');
console.log(marked.parse('Link to [Quote antigravity.txt](C:\\Users\\Tony\\Desktop\\Quote antigravity.txt)'));
console.log(marked.parse('Link to [Quote antigravity.txt](<C:\\Users\\Tony\\Desktop\\Quote antigravity.txt>)'));
console.log(marked.parse('Link to [Quote antigravity.txt](C:\\Users\\Tony\\Desktop\\Quote_antigravity.txt)'));
