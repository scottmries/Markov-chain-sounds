import OSC, time, random, itertools
c = OSC.OSCClient()
c.connect(('127.0.0.1', 10101))   # connect to PureData

beat_length = 0.65

class MarkovChain(object):
	"""Generate a second-order Markov Chain"""

	def __init__(self, values):
		self.values = values
		self.value_pairs = [(v1, v2) for v1 in xrange(len(self.values)) for v2 in xrange(len(self.values))]
		# print self.value_pairs
		self.probabilities = dict()
		self.ultimate = random.choice(xrange(len(self.values)))
		self.penultimate = random.choice(xrange(len(self.values)))
		for value_pair in self.value_pairs:
			value_probabilities = []
			total_probability = 1.0
			for i in xrange(len(self.values) - 2):
				next = random.uniform(0,total_probability)
				value_probabilities.append(next)
				total_probability -= next
			value_probabilities.append(1-sum(value_probabilities))
			value_probabilities = [0.0] + value_probabilities + [1.0]
			self.probabilities[value_pair] = sorted(value_probabilities)
		self.initialization_time = time.time()
				
		# print self.probabilities

	def getNext(self):
		probabilities = self.probabilities[(self.penultimate, self.ultimate)]
		test = random.random()
		for e, probability in enumerate(probabilities[:-1]):
			if test > probability and test < probabilities[e+1]:
				next = self.values[e]
				self.penultimate = self.ultimate
				self.ultimate = e
				return self.values[self.ultimate]

class ParametersSet(object):
	"""Set and change a set of parameters"""

	def __init__(self, paramset, OSCID, OSCsuffix):
		self.set = paramset
		self.used_params = []
		self.OSCID = OSCID
		self.OSCsuffix = OSCsuffix
		self.oscmessage = OSC.OSCMessage()
		self.oscmessage.setAddress("/%s/%s" % (OSCID, OSCsuffix))

	def resetUsedParams(self):
		self.used_params = []

	def chooseSetIndex(self):
		self.setindex = random.randint(0,len(self.set)-1)
		self.old_param = self.set[self.setindex]

	def setNewParam(self):
		self.set[self.setindex] = self.new_param

	def chooseNewParam(self):
		pass

	def testAllParamsUsed(self):
		if sorted(self.set) == sorted(list(set(self.used_params))):
			self.chooseSetIndex()
			self.chooseNewParam()
			self.setNewParam()
			self.resetUsedParams()

	def chooseAndSendParam(self):
		param = random.choice(self.set)
		self.used_params.append(param)
		self.oscmessage.clearData()
		self.oscmessage.append(param)



class FrequencySet(ParametersSet):
	"""Child change function for frequencies"""


	def chooseNewParam(self):
		move = random.randint(2,10)
		polarity = random.randint(0,1)
		polarity = (polarity*2)-1
		self.new_param = old_freq*move/(move + polarity)

class AmplitudeSet(ParametersSet):
	"""Child change function for amplitudes"""

	def chooseNewParam(self):
		self.new_param = abs(1.0 - 2.0*random.random())


class Voice(object):
	"""A voice to send out via OSC"""
	instances = []
        

	def __init__(self, freqs, lengths, shapes, pans, name, factor ):
		self.name = name
		self.freqs = MarkovChain([factor*freq for freq in freq_base][:freqs])
		self.lengths = MarkovChain([length*beat_length for length in lengths])
		self.shapes = MarkovChain(shapes)
		self.pans = MarkovChain(pans)
		self.factor = factor
		self.last_notes = [random.choice(self.freqs.values), random.choice(self.freqs.values)]
		self.last_lengths = [random.choice(self.lengths.values), random.choice(self.lengths.values)]
		self.modulation_triggers = dict()
		for (trigger_type, source) in [('note', self.freqs.values), ('length', self.lengths.values)]:
			self.setModulationTriggers(trigger_type, source)
		# self.note_modulation_trigger = [random.choice(self.freqs.values), random.choice(self.freqs.values)]
		self.next_note = time.time()
		Voice.instances.append(self)

	def setModulationTriggers(self, name, source):
		# print source
		self.modulation_triggers[name] = [random.choice(source), random.choice(source)]

	def setAddress(self, subadd):
		self.oscmsg = OSC.OSCMessage()
		self.oscmsg.setAddress("/%s/%s" % (self.name, subadd))

	def sendMsg(self, subadd, msg):
		self.setAddress(subadd)
		self.oscmsg.append(msg)
		c.send(self.oscmsg)

	def rotateNotes(self):
		print "***BEFORE*** %s" % self.freqs.values
		number_to_rotate = max(random.choice(xrange(len(self.freqs.values) - 2)) + 1, 1)
		self.freqs.values = self.freqs.values[:-1*number_to_rotate] + [self.factor*random.choice(freq_base) for i in xrange(number_to_rotate)]
		self.setModulationTriggers('note', self.freqs.values)
		print "***MODULATE NOTES*** %s: %s" % (self.name, self.freqs.values)
		base_freq_to_change = random.choice(xrange(len(freq_base)))
		while True:
			ratio = random.choice(freq_base)/random.choice(freq_base)
			if ratio > 0.5 and ratio < 2.0:
				break
		freq_base[base_freq_to_change] = freq_base[base_freq_to_change]*random.choice(freq_base)/random.choice(freq_base)

	def rotateLengths(self):
		number_to_rotate = max(random.choice(xrange(len(self.lengths.values) - 2)) + 1, 1)
		self.lengths.values = self.lengths.values[:-1*number_to_rotate] + [float(random.randint(2,4)*random.choice(self.lengths.values))/float(random.randint(1,3)) for i in xrange(number_to_rotate)]
		self.setModulationTriggers('length', self.lengths.values)
		print "***MODULATE LENGTH*** %s: %s" % (self.name, self.lengths.values)

	def rotateShapes(self):
		# self.shapes.values = self.shapes.values[:-1] + 
		pass

	def rotatePans(self):
		self.pans.values = self.pans.values[:-1] + [random.random()]
		print "***MODULATE***"

	def play(self):
		now = time.time()
		if now > self.next_note:
			note_parts = [self.freqs, self.lengths, self.shapes, self.pans]
			note = [note_part.getNext() for note_part in note_parts]
			# print bass_note[0]
			self.sendMsg("freq", note[0])
			self.sendMsg("shape", note[2])
			self.sendMsg("pans", note[3])
			self.next_note += note[1]
			self.last_notes[0] = self.last_notes[1]
			self.last_notes[1] = note[0]
			self.last_lengths[0] = self.last_lengths[1]
			self.last_lengths[1] = note[1]
			# print self.last_notes, self.note_modulation_trigger, self.last_notes == self.note_modulation_trigger
			if self.last_notes == self.modulation_triggers['note']:
				self.rotateNotes()
			if self.last_lengths == self.modulation_triggers['length']:
				self.rotateLengths()

freq_base = [8.2407*factor/divisor for factor in [float(f) for f in xrange(5)] for divisor  in [float(d) for d in xrange(5)] if divisor > 0 and ((factor/divisor >= 1 and factor/divisor <= 4) or factor)]
print len(freq_base) 

bass_voice = Voice(
	freqs = 6,
	lengths = [1.0, 0.5, 0.25],
	pans = [0.4,0.45,0.5,0.55,0.6],
	shapes = ['square','tri','sine'], 
	name = "bass",
	factor = 1.0
	)

bass_voice2 = Voice(
	freqs = 4,
	lengths = [2.0, 1.5, 1.0],
	pans = [0.4,0.45,0.5,0.55,0.6],
	shapes = ['square','tri','sine'], 
	name = "bass2",
	factor = 1.0
	)

random.shuffle(freq_base)

mid_voice = Voice(
	freqs = 5,
	lengths = [1.0, 0.5, 0.25],
	shapes = ['square','tri','sine'],
	pans = [0.2,0.3,0.35,0.4,0.6],
	name = "mid",
	factor = 4.0)

random.shuffle(freq_base)

mid_voice2 = Voice(
	freqs = 4,
	lengths = [1.0, 0.75, 0.5],
	shapes = ['square','tri','sine'],
	pans = [0.4, 0.6, 0.65, 0.7, 0.8],
	name = "mid2",
	factor = 3.5)

random.shuffle(freq_base)

mid_voice3 = Voice(
	freqs = 6,
	lengths = [0.75, 0.5, 0.25],
	shapes = ['square','tri','sine'],
	pans = [0.2, 0.21, 0.69, 0.7],
	name = "mid3",
	factor = 3.0)

# drum_voice = Voice(
# 	[200,100,0,0,0,0],
# 	[1.0, 0.75, 0.5, 0.25],
# 	['osc','noise','noise'],
# 	"drum")

# print [instance.name for instance in Voice.instances]

voices = [bass_voice, bass_voice2, mid_voice, mid_voice2, mid_voice3]

while True:
	for voice in voices:
		voice.play()
