import DefaultTable
import sstruct
import time
import string
import calendar
from fontTools.misc.textTools import safeEval, num2binary, binary2num


headFormat = """
		>	# big endian
		tableVersion:		16.16F
		fontRevision:		16.16F
		checkSumAdjustment:	l
		magicNumber:		l
							x	# pad byte
		flags:				b
		unitsPerEm:			H
		created:			8s
		modified:			8s
		xMin:				h
		yMin:				h
		xMax:				h
		yMax:				h
		macStyle:			H
		lowestRecPPEM:		H
		fontDirectionHint:	h
		indexToLocFormat:	h
		glyphDataFormat:	h
"""

class table__h_e_a_d(DefaultTable.DefaultTable):
	
	dependencies = ['maxp', 'loca']
	
	def decompile(self, data, ttFont):
		sstruct.unpack(headFormat, data, self)
		self.unitsPerEm = int(self.unitsPerEm)
		self.strings2dates()
	
	def compile(self, ttFont):
		self.modified = long(time.time() - mac_epoch_diff)
		self.dates2strings()
		data = sstruct.pack(headFormat, self)
		self.strings2dates()
		return data
	
	def strings2dates(self):
		self.created = bin2long(self.created)
		self.modified = bin2long(self.modified)
	
	def dates2strings(self):
		self.created = long2bin(self.created)
		self.modified = long2bin(self.modified)
	
	def toXML(self, writer, ttFont):
		writer.comment("Most of this table will be recalculated by the compiler")
		writer.newline()
		formatstring, names, fixes = sstruct.getformat(headFormat)
		for name in names:
			value = getattr(self, name)
			if name in ("created", "modified"):
				value = time.asctime(time.gmtime(max(0, value + mac_epoch_diff)))
			if type(value) == type(0L):
				value=int(value)
			if name in ("magicNumber", "checkSumAdjustment"):
				value = hex(value)
			elif name == "flags":
				value = num2binary(value, 16)
			writer.simpletag(name, value=value)
			writer.newline()
	
	def fromXML(self, (name, attrs, content), ttFont):
		value = attrs["value"]
		if name in ("created", "modified"):
			value = parse_date(value) - mac_epoch_diff
		elif name == "flags":
			value = binary2num(value)
		else:
			value = safeEval(value)
		setattr(self, name, value)
	
	def __cmp__(self, other):
		selfdict = self.__dict__.copy()
		otherdict = other.__dict__.copy()
		# for testing purposes, compare without the modified and checkSumAdjustment
		# fields, since they are allowed to be different.
		for key in ["modified", "checkSumAdjustment"]:
			del selfdict[key]
			del otherdict[key]
		return cmp(selfdict, otherdict)


def calc_mac_epoch_diff():
	"""calculate the difference between the original Mac epoch (1904)
	to the epoch on this machine.
	"""
	safe_epoch_t = (1971, 1, 1, 0, 0, 0, 0, 0, 0)
	safe_epoch = time.mktime(safe_epoch_t) - time.timezone
	assert time.gmtime(safe_epoch)[:6] == safe_epoch_t[:6]
	seconds1904to1971 = 60 * 60 * 24 * (365 * (1971-1904) + 17) # thanks, Laurence!
	return long(safe_epoch - seconds1904to1971)

mac_epoch_diff = calc_mac_epoch_diff()


_months = map(string.lower, calendar.month_abbr)
_weekdays = map(string.lower, calendar.day_abbr)

def parse_date(datestring):
	datestring = string.lower(datestring)
	weekday, month, day, tim, year = string.split(datestring)
	weekday = _weekdays.index(weekday)
	month = _months.index(month)
	year = int(year)
	day = int(day)
	hour, minute, second = map(int, string.split(tim, ":"))
	t = (year, month, day, hour, minute, second, weekday, 0, 0)
	return long(time.mktime(t) - time.timezone)


def bin2long(data):
	# thanks </F>!
	v = 0L
	for i in map(ord, data):
	    v = v<<8 | i
	return v

def long2bin(v, bytes=8):
	data = ""
	while v:
		data = chr(v & 0xff) + data
		v = v >> 8
	data = (bytes - len(data)) * "\0" + data
	assert len(data) == 8, "long too long"
	return data
