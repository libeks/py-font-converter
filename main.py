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

# return a js-safe representation of the rune, which can be surrounded by double quotes
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


# given a font reference (composite characters), expressed as another glyph and a transform, this transforms a point using that transform
def transformPoint(point, transform):
	(a,b,c,d,xd,yd) = transform
	(x,y) = point
	(x,y) = (a*x + b*y + xd, c*x + d*y + yd)
	return (x, y)

class Font:
	def __init__(self, font, fontpath):
		self.font = font
		self.fontpath = fontpath

	def writeFontJS(self):
		fname = 'output/'+printableString(self.font.fontname) + '.js'
		output = self.getFontOutput()
		with open(fname, 'w') as f:
			f.write(output)		
	  
	def getFontGlyphContours(self, glyphName):
		# custom replacements
		if 'Times New Roman.ttf' in self.fontpath:
			if glyphName == 'N':
				glyphName = 'glyph49'
		if 'Times New Roman Bold.ttf' in self.fontpath:
			if glyphName == 'N':
				glyphName = 'glyph1197'

		glyph = self.font[glyphName]
		
		if glyph.references:
			contours = []
			for (refGlyph, transform, _) in glyph.references:
				for contour in self.getFontGlyphContours(refGlyph):
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

	def getLigatures(self, glyphNames):
		processed = {}
		ligatures = []
		additionalGlyphNames = {}
		manualLigatures = ['ff', 'fi', 'fl', 'ft', 'fj', 'ff']
		# the following ligatures are ignored as they aren't related to English text: ['IJ', 'ij', 'LJ', 'lj', 'NJ', 'nj', 'st', 'Dz', 'dz']

		for glyphName in self.font:
			glyph = self.font[glyphName]
			match = False
			for sub in glyph.getPosSub("*"):
				# print('sub', glyphName, sub)
				if sub[1] == 'Ligature' and "'liga'" in sub[0]:
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
						additionalGlyphNames[glyphName] = arepr+brepr
						processed[arepr+brepr] = True
						match = True
				if match:
					break
		for rune in manualLigatures:
			if rune in processed:
				continue
			glyph = None
			name = None
			if rune in self.font:
				glyph = self.font[rune]
				name = rune
			underscored = rune[0] + '_' + rune[1]
			if underscored in self.font:
				glyph = self.font[underscored]
				name = underscored
			if glyph:
				ligatures.append((name, rune[0], rune[1]))
				additionalGlyphNames[name] = rune
		return ligatures, additionalGlyphNames

	def getFontOutput(self):
		glyphNames = {}
		shapes = []
		advances = []
		hints = []
		
		for rune in chars:
			runeRepr = getRuneRepresentation(rune)
			glyphName = fontforge.nameFromUnicode(ord(rune))
			glyphNames[glyphName] = rune
		ligatures, additionalGlyphNames = self.getLigatures(glyphNames)
		for key,value in additionalGlyphNames.items():
			glyphNames[key] = value
		for (glyphName, rune) in glyphNames.items():
			runeRepr = getRuneRepresentation(rune)

			if glyphName not in self.font:
				raise GlyphNotInFontExcpetion(glyphName)
			else:
				glyph = self.font[glyphName]
				advances.append('"'+runeRepr +f'": {glyph.width}')
				contours = []
				for contour in self.getFontGlyphContours(glyphName):
					contourPts = [f'[{x}, {-y}, {onCurve}]' for ((x,y), onCurve) in contour]
					contours.append('['+", ".join(contourPts)+']')
				shapes.append('"' + runeRepr + '": ['+", ".join(contours)+']')
				for kern in glyph.getPosSub("*"):
					if kern[1] == 'Pair':
						glyphName2 = kern[2]
						if glyphName2 in glyphNames:
							rune2 = glyphNames[glyphName2]
							rune2Repr = getRuneRepresentation(rune2)
							hints.append('"' + runeRepr +rune2Repr + f'": {kern[5]}')

		shapeStr = '{\n\t\t' + ", ".join(shapes) + '\n\t}'
		advanceStr = '{\n\t\t' + ", ".join(advances) + '\n\t}'
		hintStr = '{\n\t\t' + ", ".join(hints) + '\n\t}'
		ligatureStr = '[\n\t\t' + ", ".join(['"'+getRuneRepresentation(a)+getRuneRepresentation(b)+'"' for (_,a,b) in ligatures]) + '\n\t]'
		return f"""import {{Font}} from '/js/text/font.js'

		const fontRaw = {{
			familyname:"{self.font.familyname}",
			name:"{self.font.fontname}",
			fontpath: "{self.fontpath}",
			shapes: {shapeStr},
			advances: {advanceStr},
			hints: {hintStr},
			size: {self.font.em},
			ligatures: {ligatureStr},
		}}

		const font = () => new Font(fontRaw)

		export {{font as {printableString(self.font.fontname)}Font}}
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
		# 'Krungthep', # ligature spacing is wrong
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
		fontInstance = fontforge.open(fontpath)
		if (fontInstance.fontname in processedFonts) :
			print (f'fontname {fontInstance.fontname} has already been output')
			continue
		valid = True
		for elt in blacklist:
			if elt in fontInstance.fontname:
				print(f'fontname {fontInstance.fontname} filtered out for quality control issues')
				valid = False
				break
		if not valid:
			continue
		font = Font(fontInstance, fontpath)
		try:
			outfile = font.writeFontJS()
		except Exception as error:
			print(f"{fontpath} couldn't be read, {error}")
			fontInstance.close()
		else:
			print(f"Successfully exported {fontInstance.fontname}")
			with open('imports.js', 'a') as file:
				file.write(f"import {{ {printableString(fontInstance.fontname)}Font }} from '/js/text/fonts/{printableString(fontInstance.fontname)}.js'"+'\n')
			with open('exports.js', 'a') as file:
				file.write(f"{printableString(fontInstance.fontname)}Font, " + '\n')
			processedFonts[fontInstance.fontname] = True
			fontInstance.close()
		

# directory = '/System/Library/Fonts/'
# loadDirectory(directory)

fname = '/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf'
loadFont(fname)