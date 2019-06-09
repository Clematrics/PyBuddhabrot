import cmath
import ctypes
import imageio
import io
from multiprocessing import Array, Lock, Manager, Process, Value
import numpy as np
import random
import struct
from time import sleep
from threading import Thread
import os

from asciimatics.screen import Screen
from asciimatics.event import KeyboardEvent

# database is built with the following structure : (header size = 64 Bytes, with the padding of widht and height)
# 8 Bytes : integer	- number of points processed
# 2 Bytes : integer	- width of the image
# 2 Bytes : integer	- height of the image
# 8 Bytes : integer - number of random points to test and draw from
# 4 Bytes : integer	- number of iterations for any complex number
# 4 Bytes : integer	- precision, represents the number of points between the points 0+0j and 1+0j
# 8 Bytes : float	- real part of the top left corner of the image
# 8 Bytes : float	- imaginary part of the top left corner of the image
# 8 Bytes : float	- real part of the bottom right corner of the image
# 8 Bytes : float	- imaginary part of the bottom right corner of the image
# [[
#	4 Bytes : integer 	- number of iterations of a pixel
# ]]

################################               GLOBAL VARIABLES               ################################

HEADER_SIZE = 64
BATCH_SIZE = 1000000
PATH = r'buddhabrot.bin'
CPUS = os.cpu_count()

finish_order 	= Value(ctypes.c_bool, False)
shared_progress	= Value(ctypes.c_uint64, 0, lock=True)

indiv_progress = []
results = []
workers = []

width = 100
height = 100
points = 100
target_points = 0
iterations = 100
img_interval = 1000000000
img_counter = None
a = complex(-1, 1)
b = complex(1, -1)

################################              ENCODING FUNCTIONS              ################################

def encode(arr):
	buffer = []
	zeros = 0
	for k in arr:
		if k:
			if zeros:
				buffer.extend([0, zeros])
				zeros = 0
			buffer.append(k)
		else:
			zeros += 1
	return buffer

def decode(coded):
	buffer = []
	for l in coded:
		if l[0] == 0:
			buffer.extend([0] * l[1])
		else:
			buffer.extend(l)
	return buffer

def fast_add(coded, arr):
	buffer = []
	i = 0
	real_index = 0
	while i < len(coded):
		if coded[i]:
			buffer.append(coded[i] + arr[i])
			real_index += 1
		else:
			i += 1
			length = coded[i]
			part = arr[real_index, real_index + length]
			buffer.extend(encode(part))
			real_index += length
		i += 1
	return buffer

################################            DATABASE INTERACTIONS             ################################

def createFile():
	with open(PATH, 'wb+') as db:
		# we create the file header if we just created the file
		width		= int(input('Width : '))
		height		= int(input('Height : '))
		points		= int(input('Number of complex points (0 for unlimited) : '))
		iterations	= int(input('Iterations per complex : '))
		a			= complex(input('Complex number of the top left corner :'))
		b			= complex(input('Complex number of the bottom right corner :'))
		data = struct.pack('QHHQLdddd', 0, width, height, points, iterations, a.real, a.imag, b.real, b.imag)
		HEADER_SIZE = db.write(data)
		db.write(bytes([0 for j in range(width * height * 4)])) # set the cells array, each one is 4 bytes long

def loadHeader():
	""" load header data into global variables and return the progress """
	global width, height, points, iterations, a, b
	with open(PATH, 'rb+') as db:
		# reading
		db.seek(0)
		data = db.read(HEADER_SIZE)

		pack = struct.unpack('QHHQLdddd', data) # tuple : (progress, width, height, points, iter, a.real, a.imag, b.real, b.imag)
		shared_progress.value = pack[0]
		width, height, points, iterations = pack[1:5]
		a = complex(pack[5], pack[6])
		b = complex(pack[7], pack[8])

def save(array):
	with open(PATH, 'rb+') as db:
		# saving progress
		db.seek(0)
		db.write(struct.pack('Q', shared_progress.value))

		# reading current array in file
		db.seek(HEADER_SIZE)
		data = db.read(width * height * 4)
		arr = np.frombuffer(data, dtype=np.uint32).reshape((width, height))

		# adding changes
		array += arr

		# saving
		db.seek(HEADER_SIZE)
		db.write(array.tobytes())

###############################                 IMAGE RENDERING                ###############################

def renderImage():
	global gui_message, img_counter

	if img_counter == None:
		img_counter = 0
		while os.path.exists(f'buddhabrot-{img_counter}.png'):
			img_counter += 1

	with open(PATH, 'rb') as db:
		db.seek(HEADER_SIZE)
		data = db.read(width * height * 4)
		arr = np.frombuffer(data, dtype=np.uint32).reshape((width, height))
		maxi_data = np.max(arr)
		converted = (255 * (1 - np.exp(-0.5 * np.sqrt(arr)))).astype(np.uint8)
		maxi_img = np.max(converted)

		gui_message = f'Rendering image... data\'s maximum is {maxi_data} -- image\'s maximum is {maxi_img}'

		# transform = lambda x: int(255 * x / maxi) if maxi else 0
		# convert = np.vectorize(transform)
		img = np.zeros((width, height, 3), dtype=np.uint8)
		for i in range(3):
			img[:,:,i] = converted

		imageio.imwrite(f'buddhabrot-{img_counter}.png', img)
		img_counter += 1

###############################          BUDDHABROT COMPUTE FONCTIONS          ###############################

def insideCardioids(c):
	squareimag = c.imag * c.imag
	q = (c.real - .25) ** 2 + squareimag
	if q * (q + c.real - .25) < .25 * squareimag: # inside first cardioid
		return True
	return (c.real + 1) ** 2 + squareimag < .0625 # inside secnd cardioid

def sequencePath(c, iterations):
	path = []
	z = c
	i = 0
	while i < iterations and abs(z) < 2:
		z = z * z + c
		path.append(z)
		i += 1
	if i == iterations:
		return []
	return path

def getCoords(c, width, height, a, b):
	x, y = 0, 0
	try:
		x = int(width * (c.real - a.real) / (b.real - a.real))
		y = int(height * (c.imag - a.imag) / (b.imag - a.imag))
	except (ValueError, OverflowError):
		return None # out of the image
	if 0 > x or x >= width or 0 > y or y >= height:
		return None # out of the image
	return x, y

###############################          MAIN MULTITHREADED FUNCTIONS          ###############################

def work(const, shared_progress, own_progress, finish_order, result):
	width, height, points, iterations, batch_size, img_interval, a, b = const
	batch = 0
	arr = np.zeros((width, height), dtype=np.uint32)
	try:
		while not finish_order.value:
			# getting and updating overall progress
			with shared_progress.get_lock():
				batch = min(batch_size, points - shared_progress.value) if points else batch_size
				shared_progress.value += batch
			if batch <= 0:
				break

			i = 0
			own_progress.value = 0
			while i < batch:
				c = complex(random.uniform(a.real, b.real), random.uniform(b.imag, a.imag))
				if insideCardioids(c):
					continue
				path = sequencePath(c, iterations)
				if not path:
					continue

				# valid path found
				i += 1
				own_progress.value += 1
				for c in path:
					coords = getCoords(c, width, height, a, b)
					if not coords:
						continue
					x, y = coords
					arr[x, y] += 1
	except:
		raise
	finally:
		result['res'] = arr


###############################                  GUI FUNCTIONS                 ###############################

# GUI global vars
compute_loop = True
gui_on = True
gui_dim = 0, 0
gui_message = ''

def fill(string):
	lgth = len(string)
	_, wth = gui_dim
	return string + ' ' * (wth - lgth)

def gui_info(screen):
	screen.print_at(f'Press Shift + S to stop'.center(gui_dim[1], ' '), 0, 0, attr=Screen.A_BOLD, bg=Screen.COLOUR_BLUE)
	screen.print_at(''.center(gui_dim[1], ' '), 0, 1, bg=Screen.COLOUR_BLACK)	# line y = 1 reserved for mesages
	screen.print_at(fill(f'Image resolution : {width} x {height} -- ({width * height * 4 // 1024**2}Mio in memory per cpu)'), 0, 2, attr=Screen.A_BOLD, bg=Screen.COLOUR_GREEN)
	screen.print_at(fill(f'Top left is {a}, bottom right is {b}'), 0, 3, attr=Screen.A_BOLD, bg=Screen.COLOUR_GREEN)
	screen.print_at(fill(f'Numbre of complex points : {points if points else "no limit"}'), 0, 4, attr=Screen.A_BOLD, bg=Screen.COLOUR_GREEN)
	screen.print_at(fill(f'Number of cpus : {CPUS}, Size of a batch : {BATCH_SIZE}'), 0, 5, attr=Screen.A_BOLD, bg=Screen.COLOUR_GREEN)
	screen.print_at(fill(f'Iterations per point : {iterations} -- ({32 * iterations // 1024**2} Mio in memory per cpu)'), 0, 6, attr=Screen.A_BOLD, bg=Screen.COLOUR_GREEN)

def gui_print_message(screen):
	screen.print_at(gui_message.center(gui_dim[1], ' '), 0, 1, colour=Screen.COLOUR_RED, attr=Screen.A_BOLD)

def gui_progress(screen):
	# if the number of points is limited
	if target_points:
		if img_interval:
			screen.print_at(fill(f'Image progress : {shared_progress.value % img_interval, img_interval} -- {(shared_progress.value % img_interval)/ img_interval:.4%} ; Total : {shared_progress.value}'), 0, 8)
		else:
			screen.print_at(fill(f'Overall progress : {shared_progress.value, target_points} -- {shared_progress.value / target_points:.4%}'), 0, 8)

	for i in range(CPUS):
		screen.print_at(fill(f'CPU {i} : {indiv_progress[i].value, BATCH_SIZE} -- {indiv_progress[i].value / BATCH_SIZE:.4%}'), 0, 10 + i)

def handle_event(screen, event):
	global gui_message, compute_loop

	if not isinstance(event, KeyboardEvent):
		return
	if event.key_code == ord('S'):
		finish_order.value = True
		compute_loop = False
		gui_message = 'Finishing current batch and stopping'

def gui(screen):
	global gui_dim

	screen.clear()
	gui_dim = screen.dimensions
	gui_info(screen)
	while gui_on:
		if screen.has_resized():
			return

		event = screen.get_event()
		handle_event(screen, event)

		gui_progress(screen)
		gui_print_message(screen)

		screen.refresh()
		sleep(1)

def gui_main():
	try:
		while gui_on:
			Screen.wrapper(gui)
	except:
		compute_loop = False # pas propre, faire un système de abort
		print('Exception occured on the gui thread')


###############################                      MAIN                      ###############################


def main():
	global CPUS, BATCH_SIZE, img_interval, indiv_progress, results, target_points, workers, gui_message, gui_on

	# checking if the file exist, creating it if necessary
	exists = os.path.isfile(PATH)
	if not exists:
		createFile()

	# loading the header
	loadHeader()

	print('Current configuration : ')
	print(f'Image size : {width} x {height}')
	print(f'Progress : {shared_progress.value} / {points}')
	print(f'Iterations : {iterations}')
	print(f'Point a : {a} -- Point b : {b}')

	user_cpus = int(input('Number of cpu to use (0 for all): '))
	if 0 < user_cpus and user_cpus < CPUS:
		CPUS = user_cpus
	user_batch_size = input(f'Batch size (default is {BATCH_SIZE}) : ')
	if user_batch_size.isnumeric():
		BATCH_SIZE = int(user_batch_size)
	img_interval = int(input('Number of points before creating an image (0 for none): '))
	if img_interval == 0:
		img_interval = points

	manager = Manager()
	indiv_progress = [Value(ctypes.c_uint64, 0) for i in range(CPUS)]
	results = [ manager.dict() for i in range(CPUS)]

	gui_thread = Thread(target=gui_main)
	gui_thread.start()

	def work_left():
		if points:
			return shared_progress.value < points
		return True

	while compute_loop and work_left():
		target_points = 0
		if img_interval:
			target_points = shared_progress.value + img_interval - (shared_progress.value % img_interval)
		const = (width, height, target_points, iterations, BATCH_SIZE, img_interval, a, b)
		workers = [ Process(target=work, args=(const, shared_progress, indiv_progress[i], finish_order, results[i]) ) for i in range(CPUS) ]

		for w in workers:
			w.start()

		for w in workers:
			w.join()

		gui_message = 'Gathering results...'
		arr = np.zeros((width, height), dtype=np.uint32)
		for res in results:
			arr += res['res']

		gui_message = 'Saving ...'
		save(arr)
		if img_interval and shared_progress.value % img_interval == 0:
			gui_message = 'Rendering image...'
			renderImage()
		gui_message = ''

	gui_on = False
	gui_thread.join()

if __name__ == '__main__':
	try:
		main()
	finally:
		gui_on = False
