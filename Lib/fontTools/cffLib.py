"""cffLib.py -- read/write tools for Adobe CFF fonts."""

__version__ = "1.0b1"
__author__ = "jvr"

import struct, sstruct
import string
import types
import psCharStrings


cffHeaderFormat = """
	major:   B
	minor:   B
	hdrSize: B
	offSize: B
"""

class CFFFontSet:
	
	def __init__(self):
		self.fonts = {}
	
	def decompile(self, data):
		sstruct.unpack(cffHeaderFormat, data[:4], self)
		assert self.major == 1 and self.minor == 0, \
				"unknown CFF format: %d.%d" % (self.major, self.minor)
		restdata = data[self.hdrSize:]
		
		self.fontNames, restdata = readINDEX(restdata)
		topDicts, restdata = readINDEX(restdata)
		strings, restdata = readINDEX(restdata)
		strings = IndexedStrings(strings)
		globalSubrs, restdata = readINDEX(restdata)
		self.GlobalSubrs = map(psCharStrings.T2CharString, globalSubrs)
		
		for i in range(len(topDicts)):
			font = self.fonts[self.fontNames[i]] = CFFFont()
			font.GlobalSubrs = self.GlobalSubrs  # Hmm.
			font.decompile(data, topDicts[i], strings, self)  # maybe only 'on demand'?
			
	
	def compile(self):
		strings = IndexedStrings()
		XXXX
	
	def toXML(self, xmlWriter, progress=None):
		xmlWriter.newline()
		for fontName in self.fontNames:
			xmlWriter.begintag("CFFFont", name=fontName)
			xmlWriter.newline()
			font = self.fonts[fontName]
			font.toXML(xmlWriter, progress)
			xmlWriter.endtag("CFFFont")
			xmlWriter.newline()
		xmlWriter.newline()
		xmlWriter.begintag("GlobalSubrs")
		xmlWriter.newline()
		for i in range(len(self.GlobalSubrs)):
			xmlWriter.newline()
			xmlWriter.begintag("CharString", id=i)
			xmlWriter.newline()
			self.GlobalSubrs[i].toXML(xmlWriter)
			xmlWriter.endtag("CharString")
			xmlWriter.newline()
		xmlWriter.newline()
		xmlWriter.endtag("GlobalSubrs")
		xmlWriter.newline()
		xmlWriter.newline()
	
	def fromXML(self, (name, attrs, content)):
		xxx


class IndexedStrings:
	
	def __init__(self, strings=None):
		if strings is None:
			strings = []
		self.strings = strings
	
	def __getitem__(self, SID):
		if SID < cffStandardStringCount:
			return cffStandardStrings[SID]
		else:
			return self.strings[SID - cffStandardStringCount]
	
	def getSID(self, s):
		if not hasattr(self, "stringMapping"):
			self.buildStringMapping()
		if cffStandardStringMapping.has_key(s):
			SID = cffStandardStringMapping[s]
		if self.stringMapping.has_key(s):
			SID = self.stringMapping[s]
		else:
			SID = len(self.strings) + cffStandardStringCount
			self.strings.append(s)
			self.stringMapping[s] = SID
		return SID
	
	def getStrings(self):
		return self.strings
	
	def buildStringMapping(self):
		self.stringMapping = {}
		for index in range(len(self.strings)):
			self.stringMapping[self.strings[index]] = index + cffStandardStringCount


class CFFFont:
	
	defaults = psCharStrings.topDictDefaults
	
	def __init__(self):
		pass
	
	def __getattr__(self, attr):
		if not self.defaults.has_key(attr):
			raise AttributeError, attr
		return self.defaults[attr]
	
	def fromDict(self, dict):
		self.__dict__.update(dict)
	
	def decompile(self, data, topDictData, strings, fontSet):
		top = psCharStrings.TopDictDecompiler(strings)
		top.decompile(topDictData)
		self.fromDict(top.getDict())
		
		# get private dict
		size, offset = self.Private
		#print "YYY Private (size, offset):", size, offset
		privateData = data[offset:offset+size]
		self.Private = PrivateDict()
		self.Private.decompile(data[offset:], privateData, strings)
		
		# get raw charstrings
		#print "YYYY CharStrings offset:", self.CharStrings
		rawCharStrings, restdata = readINDEX(data[self.CharStrings:])
		nGlyphs = len(rawCharStrings)
		
		# get charset (or rather: get glyphNames)
		charsetOffset = self.charset
		if charsetOffset == 0:
			xxx  # standard charset
		else:
			#print "YYYYY charsetOffset:", charsetOffset
			format = ord(data[charsetOffset])
			if format == 0:
				xxx
			elif format == 1:
				charSet = parseCharsetFormat1(nGlyphs, 
						data[charsetOffset+1:], strings)
			elif format == 2:
				charSet = parseCharsetFormat2(nGlyphs, 
						data[charsetOffset+1:], strings)
			elif format == 3:
				xxx
			else:
				xxx
		self.charset = charSet
		
		assert len(charSet) == nGlyphs
		self.CharStrings = charStrings = {}
		if self.CharstringType == 2:
			# Type 2 CharStrings
			charStringClass = psCharStrings.T2CharString
		else:
			# Type 1 CharStrings
			charStringClass = psCharStrings.T1CharString
		for i in range(nGlyphs):
			charStrings[charSet[i]] = charStringClass(rawCharStrings[i])
		assert len(charStrings) == nGlyphs
		
		# XXX Encoding!
		encoding = self.Encoding
		if encoding not in (0, 1):
			# encoding is an _offset_ from the beginning of 'data' to an encoding subtable
			XXX
			self.Encoding = encoding
	
	def getGlyphOrder(self):
		return self.charset
	
	def setGlyphOrder(self, glyphOrder):
		self.charset = glyphOrder
	
	def decompileAllCharStrings(self):
		if self.CharstringType == 2:
			# Type 2 CharStrings
			decompiler = psCharStrings.SimpleT2Decompiler(self.Private.Subrs, self.GlobalSubrs)
			for charString in self.CharStrings.values():
				if charString.needsDecompilation():
					decompiler.reset()
					decompiler.execute(charString)
		else:
			# Type 1 CharStrings
			for charString in self.CharStrings.values():
				charString.decompile()
	
	def toXML(self, xmlWriter, progress=None):
		xmlWriter.newline()
		# first dump the simple values
		self.toXMLSimpleValues(xmlWriter)
		
		# dump charset
		# XXX
		
		# decompile all charstrings
		if progress:
			progress.setlabel("Decompiling CharStrings...")
		self.decompileAllCharStrings()
		
		# dump private dict
		xmlWriter.begintag("Private")
		xmlWriter.newline()
		self.Private.toXML(xmlWriter)
		xmlWriter.endtag("Private")
		xmlWriter.newline()
		
		self.toXMLCharStrings(xmlWriter, progress)
	
	def toXMLSimpleValues(self, xmlWriter):
		keys = self.__dict__.keys()
		keys.remove("CharStrings")
		keys.remove("Private")
		keys.remove("charset")
		keys.remove("GlobalSubrs")
		keys.sort()
		for key in keys:
			value = getattr(self, key)
			if key == "Encoding":
				if value == 0:
					# encoding is (Adobe) Standard Encoding
					value = "StandardEncoding"
				elif value == 1:
					# encoding is Expert Encoding
					value = "ExpertEncoding"
			if type(value) == types.ListType:
				value = string.join(map(str, value), " ")
			else:
				value = str(value)
			xmlWriter.begintag(key)
			if hasattr(value, "toXML"):
				xmlWriter.newline()
				value.toXML(xmlWriter)
				xmlWriter.newline()
			else:
				xmlWriter.write(value)
			xmlWriter.endtag(key)
			xmlWriter.newline()
		xmlWriter.newline()
	
	def toXMLCharStrings(self, xmlWriter, progress=None):
		charStrings = self.CharStrings
		xmlWriter.newline()
		xmlWriter.begintag("CharStrings")
		xmlWriter.newline()
		glyphNames = charStrings.keys()
		glyphNames.sort()
		for glyphName in glyphNames:
			if progress:
				progress.setlabel("Dumping 'CFF ' table... (%s)" % glyphName)
				progress.increment()
			xmlWriter.newline()
			charString = charStrings[glyphName]
			xmlWriter.begintag("CharString", name=glyphName)
			xmlWriter.newline()
			charString.toXML(xmlWriter)
			xmlWriter.endtag("CharString")
			xmlWriter.newline()
		xmlWriter.newline()
		xmlWriter.endtag("CharStrings")
		xmlWriter.newline()


class PrivateDict:
	
	defaults = psCharStrings.privateDictDefaults
	
	def __init__(self):
		pass
	
	def decompile(self, data, privateData, strings):
		p = psCharStrings.PrivateDictDecompiler(strings)
		p.decompile(privateData)
		self.fromDict(p.getDict())
		
		# get local subrs
		#print "YYY Private.Subrs:", self.Subrs
		chunk = data[self.Subrs:]
		localSubrs, restdata = readINDEX(chunk)
		self.Subrs = map(psCharStrings.T2CharString, localSubrs)
	
	def toXML(self, xmlWriter):
		xmlWriter.newline()
		keys = self.__dict__.keys()
		keys.remove("Subrs")
		for key in keys:
			value = getattr(self, key)
			if type(value) == types.ListType:
				value = string.join(map(str, value), " ")
			else:
				value = str(value)
			xmlWriter.begintag(key)
			xmlWriter.write(value)
			xmlWriter.endtag(key)
			xmlWriter.newline()
		# write subroutines
		xmlWriter.newline()
		xmlWriter.begintag("Subrs")
		xmlWriter.newline()
		for i in range(len(self.Subrs)):
			xmlWriter.newline()
			xmlWriter.begintag("CharString", id=i)
			xmlWriter.newline()
			self.Subrs[i].toXML(xmlWriter)
			xmlWriter.endtag("CharString")
			xmlWriter.newline()
		xmlWriter.newline()
		xmlWriter.endtag("Subrs")
		xmlWriter.newline()
		xmlWriter.newline()
	
	def __getattr__(self, attr):
		if not self.defaults.has_key(attr):
			raise AttributeError, attr
		return self.defaults[attr]
	
	def fromDict(self, dict):
		self.__dict__.update(dict)


def readINDEX(data):
	count, = struct.unpack(">H", data[:2])
	count = int(count)
	offSize = ord(data[2])
	data = data[3:]
	offsets = []
	for index in range(count+1):
		chunk = data[index * offSize: (index+1) * offSize]
		chunk = '\0' * (4 - offSize) + chunk
		offset, = struct.unpack(">L", chunk)
		offset = int(offset)
		offsets.append(offset)
	data = data[(count+1) * offSize:]
	prev = offsets[0]
	stuff = []
	for next in offsets[1:]:
		chunk = data[prev-1:next-1]
		assert len(chunk) == next - prev
		stuff.append(chunk)
		prev = next
	data = data[next-1:]
	return stuff, data


def parseCharsetFormat1(nGlyphs, data, strings):
	charSet = ['.notdef']
	count = 1
	while count < nGlyphs:
		first = int(struct.unpack(">H", data[:2])[0])
		nLeft = ord(data[2])
		data = data[3:]
		for SID in range(first, first+nLeft+1):
			charSet.append(strings[SID])
		count = count + nLeft + 1
	return charSet


def parseCharsetFormat2(nGlyphs, data, strings):
	charSet = ['.notdef']
	count = 1
	while count < nGlyphs:
		first = int(struct.unpack(">H", data[:2])[0])
		nLeft = int(struct.unpack(">H", data[2:4])[0])
		data = data[4:]
		for SID in range(first, first+nLeft+1):
			charSet.append(strings[SID])
		count = count + nLeft + 1
	return charSet


# The 391 Standard Strings as used in the CFF format.
# from Adobe Technical None #5176, version 1.0, 18 March 1998

cffStandardStrings = ['.notdef', 'space', 'exclam', 'quotedbl', 'numbersign', 
		'dollar', 'percent', 'ampersand', 'quoteright', 'parenleft', 'parenright', 
		'asterisk', 'plus', 'comma', 'hyphen', 'period', 'slash', 'zero', 'one', 
		'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'colon', 
		'semicolon', 'less', 'equal', 'greater', 'question', 'at', 'A', 'B', 'C', 
		'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 
		'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'bracketleft', 'backslash', 
		'bracketright', 'asciicircum', 'underscore', 'quoteleft', 'a', 'b', 'c', 
		'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 
		's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'braceleft', 'bar', 'braceright', 
		'asciitilde', 'exclamdown', 'cent', 'sterling', 'fraction', 'yen', 'florin', 
		'section', 'currency', 'quotesingle', 'quotedblleft', 'guillemotleft', 
		'guilsinglleft', 'guilsinglright', 'fi', 'fl', 'endash', 'dagger', 
		'daggerdbl', 'periodcentered', 'paragraph', 'bullet', 'quotesinglbase', 
		'quotedblbase', 'quotedblright', 'guillemotright', 'ellipsis', 'perthousand', 
		'questiondown', 'grave', 'acute', 'circumflex', 'tilde', 'macron', 'breve', 
		'dotaccent', 'dieresis', 'ring', 'cedilla', 'hungarumlaut', 'ogonek', 'caron', 
		'emdash', 'AE', 'ordfeminine', 'Lslash', 'Oslash', 'OE', 'ordmasculine', 'ae', 
		'dotlessi', 'lslash', 'oslash', 'oe', 'germandbls', 'onesuperior', 
		'logicalnot', 'mu', 'trademark', 'Eth', 'onehalf', 'plusminus', 'Thorn', 
		'onequarter', 'divide', 'brokenbar', 'degree', 'thorn', 'threequarters', 
		'twosuperior', 'registered', 'minus', 'eth', 'multiply', 'threesuperior', 
		'copyright', 'Aacute', 'Acircumflex', 'Adieresis', 'Agrave', 'Aring', 
		'Atilde', 'Ccedilla', 'Eacute', 'Ecircumflex', 'Edieresis', 'Egrave', 
		'Iacute', 'Icircumflex', 'Idieresis', 'Igrave', 'Ntilde', 'Oacute', 
		'Ocircumflex', 'Odieresis', 'Ograve', 'Otilde', 'Scaron', 'Uacute', 
		'Ucircumflex', 'Udieresis', 'Ugrave', 'Yacute', 'Ydieresis', 'Zcaron', 
		'aacute', 'acircumflex', 'adieresis', 'agrave', 'aring', 'atilde', 'ccedilla', 
		'eacute', 'ecircumflex', 'edieresis', 'egrave', 'iacute', 'icircumflex', 
		'idieresis', 'igrave', 'ntilde', 'oacute', 'ocircumflex', 'odieresis', 
		'ograve', 'otilde', 'scaron', 'uacute', 'ucircumflex', 'udieresis', 'ugrave', 
		'yacute', 'ydieresis', 'zcaron', 'exclamsmall', 'Hungarumlautsmall', 
		'dollaroldstyle', 'dollarsuperior', 'ampersandsmall', 'Acutesmall', 
		'parenleftsuperior', 'parenrightsuperior', 'twodotenleader', 'onedotenleader', 
		'zerooldstyle', 'oneoldstyle', 'twooldstyle', 'threeoldstyle', 'fouroldstyle', 
		'fiveoldstyle', 'sixoldstyle', 'sevenoldstyle', 'eightoldstyle', 
		'nineoldstyle', 'commasuperior', 'threequartersemdash', 'periodsuperior', 
		'questionsmall', 'asuperior', 'bsuperior', 'centsuperior', 'dsuperior', 
		'esuperior', 'isuperior', 'lsuperior', 'msuperior', 'nsuperior', 'osuperior', 
		'rsuperior', 'ssuperior', 'tsuperior', 'ff', 'ffi', 'ffl', 'parenleftinferior', 
		'parenrightinferior', 'Circumflexsmall', 'hyphensuperior', 'Gravesmall', 
		'Asmall', 'Bsmall', 'Csmall', 'Dsmall', 'Esmall', 'Fsmall', 'Gsmall', 'Hsmall', 
		'Ismall', 'Jsmall', 'Ksmall', 'Lsmall', 'Msmall', 'Nsmall', 'Osmall', 'Psmall', 
		'Qsmall', 'Rsmall', 'Ssmall', 'Tsmall', 'Usmall', 'Vsmall', 'Wsmall', 'Xsmall', 
		'Ysmall', 'Zsmall', 'colonmonetary', 'onefitted', 'rupiah', 'Tildesmall', 
		'exclamdownsmall', 'centoldstyle', 'Lslashsmall', 'Scaronsmall', 'Zcaronsmall', 
		'Dieresissmall', 'Brevesmall', 'Caronsmall', 'Dotaccentsmall', 'Macronsmall', 
		'figuredash', 'hypheninferior', 'Ogoneksmall', 'Ringsmall', 'Cedillasmall', 
		'questiondownsmall', 'oneeighth', 'threeeighths', 'fiveeighths', 'seveneighths', 
		'onethird', 'twothirds', 'zerosuperior', 'foursuperior', 'fivesuperior', 
		'sixsuperior', 'sevensuperior', 'eightsuperior', 'ninesuperior', 'zeroinferior', 
		'oneinferior', 'twoinferior', 'threeinferior', 'fourinferior', 'fiveinferior', 
		'sixinferior', 'seveninferior', 'eightinferior', 'nineinferior', 'centinferior', 
		'dollarinferior', 'periodinferior', 'commainferior', 'Agravesmall', 
		'Aacutesmall', 'Acircumflexsmall', 'Atildesmall', 'Adieresissmall', 'Aringsmall', 
		'AEsmall', 'Ccedillasmall', 'Egravesmall', 'Eacutesmall', 'Ecircumflexsmall', 
		'Edieresissmall', 'Igravesmall', 'Iacutesmall', 'Icircumflexsmall', 
		'Idieresissmall', 'Ethsmall', 'Ntildesmall', 'Ogravesmall', 'Oacutesmall', 
		'Ocircumflexsmall', 'Otildesmall', 'Odieresissmall', 'OEsmall', 'Oslashsmall', 
		'Ugravesmall', 'Uacutesmall', 'Ucircumflexsmall', 'Udieresissmall', 
		'Yacutesmall', 'Thornsmall', 'Ydieresissmall', '001.000', '001.001', '001.002', 
		'001.003', 'Black', 'Bold', 'Book', 'Light', 'Medium', 'Regular', 'Roman', 
		'Semibold'
]

cffStandardStringCount = 391
assert len(cffStandardStrings) == cffStandardStringCount
# build reverse mapping
cffStandardStringMapping = {}
for _i in range(cffStandardStringCount):
	cffStandardStringMapping[cffStandardStrings[_i]] = _i

