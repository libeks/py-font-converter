# from fontTools import ttLib
# from ttfquery import describe
import fontforge
import string
import os

chars = string.digits + string.ascii_letters + string.punctuation + ' '


processedFonts = {}

class GlyphNotInFontExcpetion(Exception):
    def __init__(self, message, error_code):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"GlyphNotInFontException: {self.message}"



def writeFontJS(font, fontpath):
	fname = 'output/'+printableString(font.fontname) + '.js'
	output = getFontOutput(font, fontpath)
	with open(fname, 'w') as f:
		f.write(output)		
  

# return a js-safe representation of the rune
def getRuneRepresentation(rune):
	if rune == '"':
		return "\\\""
	if rune == '\\':
		return "\\\\"
	return rune

# return a string that can be used as a js variable name (more precisedly, export alias)
def printableString(str):
	str = str.replace('-', '')
	str = str.replace(' ', '')
	str = str.replace('.', '') 
	return str


def transformPoint(point, transform):
	(a,b,c,d,xd,yd) = transform
	(x,y) = point
	(x,y) = (a*x + b*y + xd, c*x + d*y + yd)
	return (x, y)

def getFontGlyphContours(font, glyphName):
	glyph = font[glyphName]
	
	if glyph.references:
		contours = []
		for (refGlyph, transform, _) in glyph.references:
			for contour in getFontGlyphContours(font, refGlyph):
				contourPts = []
				for (point, onCurve) in contour:
					contourPts.append((transformPoint(point, transform), onCurve))
				contours.append(contourPts)
		return contours
	for layerName in glyph.layers:
		layer = glyph.layers[layerName]
		if layerName == 'Back':
			continue
		contours = []
		for contour in layer:
			contourPts = []
			for point in contour:
				contourPts.append(((point.x, point.y), point.on_curve))
			contours.append(contourPts)
		return contours

def getLigatures(font, glyphNames):
	for glyphName in font:
		# print(' ligature', glyph,glyph.getPosSub("*"))
		glyph = font[glyphName]
		# print('glyph', glyphName, glyph)
		for sub in glyph.getPosSub("*"):
			if sub[1] == 'Ligature' and "'liga'" in sub[0]:
				# print(sub)
				elts = sub[2:]
				if len(elts)> 2:
					print(f'ignoring ligature {glyphName} for {elts}')
					continue
				a,b = sub[2], sub[3]
				if a in glyphNames and b in glyphNames:
					print(f'found ligature {glyphName} for {a} and {b}', sub[0])
					arepr = getRuneRepresentation(glyphNames[a])
					brepr = getRuneRepresentation(glyphNames[b])
					ligatures.append((glyphName, arepr, brepr))
					glyphNames[glyphName] = arepr+brepr
	return ligatures, additionalGlyphNames

def getFontOutput(font, fontpath):
	glyphNames = {}
	shapes = []
	advances = []
	hints = []
	# leftBearings = []
	# for lookup in font.gsub_lookups:
	# 	print('gsub lookups',lookup, font.getLookupInfo(lookup), font.getLookupSubtables(lookup))

	# scan over all glyphs to see if there are ligatures

	# if 'fi' in font:
	# 	glyph = font['fi']
	for rune in chars:
		runeRepr = getRuneRepresentation(rune)
		glyphName = fontforge.nameFromUnicode(ord(rune))
		glyphNames[glyphName] = rune
	ligatures = []
	for glyphName in font:
		# print(' ligature', glyph,glyph.getPosSub("*"))
		glyph = font[glyphName]
		# print('glyph', glyphName, glyph)
		for sub in glyph.getPosSub("*"):
			if sub[1] == 'Ligature' and "'liga'" in sub[0]:
				# print(sub)
				elts = sub[2:]
				if len(elts)> 2:
					print(f'ignoring ligature {glyphName} for {elts}')
					continue
				a,b = sub[2], sub[3]
				if a in glyphNames and b in glyphNames:
					print(f'found ligature {glyphName} for {a} and {b}', sub[0])
					arepr = getRuneRepresentation(glyphNames[a])
					brepr = getRuneRepresentation(glyphNames[b])
					ligatures.append((glyphName, arepr, brepr))
					glyphNames[glyphName] = arepr+brepr
	# print('glyphNames', glyphNames)
	for (glyphName, rune) in glyphNames.items():
		# rune = glyphNames
		runeRepr = getRuneRepresentation(rune)

		# glyphName = fontforge.nameFromUnicode(ord(rune))
		if glyphName not in font:
			raise GlyphNotInFontExcpetion(glyphName)
		else:
			glyph = font[glyphName]
			advances.append('"'+runeRepr +f'": {glyph.width}')
			# if glyph.left_side_bearing != 0:
			# 	leftBearings.append(f'"{runeRepr}": {glyph.left_side_bearing}')
		
			# print(f'glyph {rune}:{glyphName} has horizontal components {glyph.horizontalComponents}, variants {glyph.horizontalVariants}')
			# print(f'glyph {rune}:{glyphName} has references {glyph.references}')
			# for layerName in glyph.layers:
			# 	layer = glyph.layers[layerName]
			# 	print(f'glyph {rune}:{glyphName} has layer {layerName} with {len(layer)} elements')

			# 	if layerName == 'Back':
			# 		continue
			# 	contours = []
			# 	for contour in layer:
			# 		contourPts = []
			# 		for point in contour:
			# 			contourPts.append(f'[{point.x}, {-point.y}, {point.on_curve}]')
			# 		contours.append('['+", ".join(contourPts)+']')
			# 	shapes.append('"' + runeRepr + '": ['+", ".join(contours)+']')
			contours = []
			for contour in getFontGlyphContours(font, glyphName):
				contourPts = [f'[{x}, {-y}, {onCurve}]' for ((x,y), onCurve) in contour]
				contours.append('['+", ".join(contourPts)+']')
			shapes.append('"' + runeRepr + '": ['+", ".join(contours)+']')
			for kern in glyph.getPosSub("*"):
				if kern[1] == 'Pair':
					# print(f'{rune}: pair substitution', kern)
					glyphName2 = kern[2]
					if glyphName2 in glyphNames:
						rune2 = glyphNames[glyphName2]
						rune2Repr = getRuneRepresentation(rune2)
						hints.append('"' + runeRepr +rune2Repr + f'": {kern[5]}')
				# else:
				# 	print(f'{rune}: ignoring subtable', kern)

	shapeStr = '{\n\t\t' + ", ".join(shapes) + '\n\t}'
	advanceStr = '{\n\t\t' + ", ".join(advances) + '\n\t}'
	hintStr = '{\n\t\t' + ", ".join(hints) + '\n\t}'
	ligatureStr = '[\n\t\t' + ", ".join(['"'+getRuneRepresentation(a)+getRuneRepresentation(b)+'"' for (_,a,b) in ligatures]) + '\n\t]'
	# leftBearingStr = '{\n\t\t' + ", ".join(leftBearings)+ '\n\t}'
	return f"""import {{Font}} from '/js/text/font.js'

	const fontRaw = {{
		familyname:"{font.familyname}",
		name:"{font.fontname}",
		fontpath: "{fontpath}",
		shapes: {shapeStr},
		advances: {advanceStr},
		hints: {hintStr},
		size: {font.em},
		ligatures: {ligatureStr},
	}}

	const font = () => new Font(fontRaw)

	export {{font as {printableString(font.fontname)}Font}}
	"""

	
def loadDirectory(dir):
	processedFilenames = []
	try:
		with open('processed.log', 'r') as f:
			lines = f.readlines()
			print(lines)
			processedFilenames = [line.strip() for line in lines]
	except:
		pass

	blacklist = [
	# these files can't be read by fontforge
	'Iowan Old Style', 'SFIndia.ttc', 'DecoType', 'NISC18030', 'SuperClarendon','Ayuthaya', 'Songti',
	]
	for root, dirs,files in os.walk(dir):
		for file in files:
			filename = os.path.join(root, file)
			if filename in processedFilenames:
				print(f'already processed {filename}')
				continue
			# print('file', root, file, filename)
			valid = True
			for elt in blacklist:
				if elt in filename:
					print(f'skipping {filename}')
					valid = False
					break
			if not valid:
				continue
			if (filename.endswith('.ttc') or filename.endswith('.ttf')):
				print(f'Reading file {filename}')
				with open("processed.log", 'a') as f:
					f.write(f'{filename}' + '\n')
				loadFont(filename)
			else:
				print(f'Skipping file {filename}')

def loadFont(fname):
	blacklist = [
		# these are filtered for quality control issues
		'Chalkduster', # too curvy
		'Brush', # too curvy
		'BradleyHandITCTT', # ugly shapes
		'AppleSDGothic', # wrong 'Te' kerning
		'AppleSymbols', # wrong 'Te' kerning
		'ArialUnicode', # wrong 'Te' kerning
		'Athelas-Bold', # wrong 'Te' kerning
		'Avenir', # wrong 'Te' kerning
		'BanglaSangam', # wrong 'Te' kerning
		'BigCaslon', # wrong 'Te' kerning
		'BodoniSvtyTwoITCTT', # wrong 'Te' kerning
		'Didot-Bold', # wrong kerning
		'EuphemiaUCAS',
		'Futura-Medium', # incorrect 'Te' and 'To' kerning, might be processing the file wrong
		'Galvji',
		'Geneva',
		'GujaratiSangam',
		'Gurmukhi',
		'HiraginoSans',
		'HiraKaku',
		'InaiMathi',
		'KannadaSangam',
		'KefaIII', # incorrect 'Te' and 'To' kerning, might be processing the file wrong
		'Khmer',
		'Kohinoor',
		'Lao',
		'Malayalam',
		'MicrosoftSansSerif',
		'MuktaMahee',
		'Myanmar',
		# 'NewYork', # missing characters? 'fi' renders without the 'i'
		'Oriya',
		'Papyrus',
		# 'PTMono', # missing 'i' character
		# 'PTSans', # missing 'i' character
		# 'PTSerif', # missing 'i' character
		'Sathu',
		'Seravek',
		'ShreeDev',
		'SinhalaSangam',
		'STHeiti',
		'Sukhumvit',
		'Tamil',
		'Telugu',
		'Thonburi',
		'Verdana-Bold'

	]
	print('fonts in file', fontforge.fontsInFile(fname))
	fonts = fontforge.fontsInFile(fname)
	for fontName in fonts:
		fontpath = fname + '(' + fontName + ')'
		font = fontforge.open(fontpath)
		if (font.fontname in processedFonts) :
			print (f'fontname {font.fontname} has already been output')
			continue
		valid = True
		for elt in blacklist:
			if elt in font.fontname:
				print(f'fontname {font.fontname} filtered out for quality control issues')
				valid = False
				break
		if not valid:
			continue
		try:
			outfile = writeFontJS(font, fontpath)
		except Exception as error:
			print(f"{fontpath} couldn't be read, {error}")
			font.close()
		else:
			print(f"Successfully exported {font.fontname}")
			with open('imports.js', 'a') as file:
				file.write(f"import {{ {printableString(font.fontname)}Font }} from '/js/text/fonts/{printableString(font.fontname)}.js'"+'\n')
			with open('exports.js', 'a') as file:
				file.write(f"{printableString(font.fontname)}Font, " + '\n')
			processedFonts[font.fontname] = True
			font.close()
		

# directory = '/System/Library/Fonts/'
# loadDirectory(directory)

fname = '/System/Library/Fonts/Supplemental/Futura.ttc'
loadFont(fname)