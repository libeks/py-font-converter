# from fontTools import ttLib
# from ttfquery import describe
import fontforge
import string
import os

chars = string.digits + string.ascii_letters + string.punctuation + ' '


class GlyphNotInFontExcpetion(Exception):
    def __init__(self, message, error_code):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"GlyphNotInFontException: {self.message}"



def writeFontJS(font):
	fname = 'output/'+printableString(font.fontname) + '.js'
	output = getFontOutput(font)
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


def getFontOutput(font):
	glyphNames = {}
	shapes = []
	advances = []
	hints = []
	for rune in chars:
		runeRepr = getRuneRepresentation(rune)
		glyphName = fontforge.nameFromUnicode(ord(rune))
		glyphNames[glyphName] = rune
	for rune in chars:
		runeRepr = getRuneRepresentation(rune)
		glyphName = fontforge.nameFromUnicode(ord(rune))
		if glyphName not in font:
			raise GlyphNotInFontExcpetion(glyphName)
		else:
			glyph = font[glyphName]
			advances.append('"'+runeRepr +f'": {glyph.width}')
		
			for layerName in glyph.layers:
				layer = glyph.layers[layerName]
				if layerName == 'Back':
					continue
				contours = []
				for contour in layer:
					contourPts = []
					for point in contour:
						contourPts.append(f'[{point.x}, {-point.y}, {point.on_curve}]')
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
	advanceStr = '{\n\t\t' + ", ".join(advances)+ '\n\t}'
	hintStr = '{\n\t\t' + ", ".join(hints)+ '\n\t}'
	return f"""import {{Font}} from '/js/text/fonts/fonts.js'

	const fontRaw = {{
		familyname:"{font.familyname}'",
		name:"{font.fontname}",
		shapes: {shapeStr},
		advances: {advanceStr},
		hints: {hintStr},
		size: {font.em},
	}}

	const font = new Font(fontRaw)

	export {{font as {printableString(font.fontname)}Font}}
	"""

	
def loadDirectory(dir):

	with open('log.txt') as f:
		lines = f.readlines()
		print(lines)
		filenames = [line.strip() for line in lines]
	blacklist = ['Iowan Old Style', 'SFIndia.ttc', 'DecoType', 'NISC18030', 'SuperClarendon']
	for root, dirs,files in os.walk(dir):
		for file in files:
			filename = os.path.join(root, file)
			if filename in filenames:
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
				with open("log.txt", 'a') as f:
					f.write(f'{filename}' + '\n')
				loadFont(filename)
				
			else:
				print(f'Skipping file {filename}')

def loadFont(fname):
	print('fonts in file', fontforge.fontsInFile(fname))
	fonts = fontforge.fontsInFile(fname)
	for fontName in fonts:
		fontpath = fname + '(' + fontName + ')'
		font = fontforge.open(fontpath)
		try:
			writeFontJS(font)
		except Exception as error:
			print(f"{fontpath} couldn't be read, {error}")
		else:
			print(f"Successfully exported {font.fontname}")
			font.close()
		

directory = '/System/Library/Fonts/'
loadDirectory(directory)

# fname = '/System/Library/Fonts/Supplemental/Iowan Old Style.ttc'
# loadFont(fname)