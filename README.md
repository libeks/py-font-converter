# py-font-converter

Py script to convert TrueType fonts to SVG JS format

# Running

```
rm output/*.js
fontforge -script main.py
sort -o imports.js imports.js
sort -o exports.js exports.js
```

# VENV

`source .venv/bin/activate`
