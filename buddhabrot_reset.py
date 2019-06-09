import io
import struct

HEADER_SIZE = 64
PATH = r'buddhabrot.bin'

def loadHeader(db):
	db.seek(0)
	data = db.read(HEADER_SIZE)
	pack = struct.unpack('QHHQLdddd', data)
	# pack contains progress, width, height, points, iter, a.real, a.imag, b.real, b.imag
	context = {}
	context['width'], context['height'], context['points'], context['iterations'] = pack[1:5]
	context['a'] = complex(pack[5], pack[6])
	context['b'] = complex(pack[7], pack[8])
	return context

user_input = input(f'Are you sure you want to reset all the computation result stored in {PATH} ? Type Yes if so\n')
if user_input == 'Yes' or  user_input == 'yes':
	with open(PATH, 'rb+') as db:
		context = loadHeader(db)
		db.seek(0)
		db.write(struct.pack('Q', 0))
		db.seek(HEADER_SIZE)
		db.write(bytes([0 for i in range(context['width'] * context['height'] * 4)]))

	print('Reset done!')
else:
	print('The reset was cancelled.')