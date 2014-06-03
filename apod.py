import requests
import re
import shutil
from PIL import Image, ImageFont, ImageDraw
import textwrap

APOD = 'http://apod.nasa.gov/apod/astropix.html'
APOD_BASE = 'http://apod.nasa.gov/apod/'
RESX = 1920
RESY = 1080
TASKBAR_HEIGHT = 30
EFFECTIVE_RESY = RESY - TASKBAR_HEIGHT
MAX_LINE_LEN = 100

def get_html(url=APOD):
	return requests.get(url).text

def get_img_url(apod_html):
	p = re.compile(r'<a href="(image/[^>]*)">')
	m = p.findall(apod_html)
	return APOD_BASE + m[0]

def get_title(apod_html):
	p = re.compile(r'<center>\n<b> (.*) </b> <br>')
	m = p.findall(apod_html)
	return m[0]

def get_img(apod_html, out_img_fname='temp.jpg'):
	url = get_img_url(apod_html)
	response = requests.get(url, stream=True)
	outf = open(out_img_fname, 'wb')
	shutil.copyfileobj(response.raw, outf)
	outf.close()
	return True

def get_explanation(apod_html):
	p = re.compile(r'<b> Explanation: </b>(.*?)<p> <center>', re.DOTALL)
	m = p.findall(apod_html)
	return strip_html_and_newlines(m[0]).strip()

def strip_html_and_newlines(txt):
	temp = re.sub('<[^<]+?>', '', txt)
	temp = re.sub('\s+', ' ', temp)
	return temp

def resize_and_pad(img):
	width, height = img.size
	aspect_ratio = width / height
	desired_aspect_ratio = RESX / EFFECTIVE_RESY
	if aspect_ratio == desired_aspect_ratio:
		#no padding necessary
		new_width = RESX
		new_height = RESY
	elif aspect_ratio < desired_aspect_ratio:
		#pad on left and right
		resize_ratio = EFFECTIVE_RESY / height
		new_width = round(width * resize_ratio)
		new_height = EFFECTIVE_RESY
	else:
		#pad on top and bottom
		resize_ratio = RESX / width
		new_width = RESX
		new_height = round(height * resize_ratio)
	img = img.resize((new_width, new_height), Image.ANTIALIAS)
	out_img = Image.new('RGB', (RESX, RESY), "black")
	x_offset = (RESX - new_width) // 2
	y_offset = (EFFECTIVE_RESY - new_height) // 2
	out_img.paste(img, (x_offset, y_offset))
	return out_img

def get_text_width_and_height(text, font):
	#is there a better way to do this? We shouldn't need to 
	#create a new image just to figure out the size of text
	#in a certain font
	im = Image.new("RGB",(0,0),"black")
	draw = ImageDraw.Draw(im)
	text_width, text_height = draw.textsize(text, font=font)
	return text_width, text_height

def get_text_width(text, font):
	return get_text_width_and_height(text, font)[0]

def get_text_height(text, font):
	return get_text_width_and_height(text, font)[1]

def split_text_into_lines(text, width, font):
	words = text.strip().split()
	#put the first word on the first line to start
	#always put spaces after words so we don't have to worry about
	#adding them at the beginning of lines
	#spaces at the end of lines are inconsequential
	lines = [words[0] + ' ']
	words = words[1:]
	for word in words:
		if get_text_width(lines[-1] + word, font) <= width:
			#current word fits in current line
			lines[-1] += word + ' '
		else:
			#current word does not fit in current line
			#remove the space from the current line
			lines[-1] = lines[-1][:-1]
			#make a new line and add the word
			lines.append(word + ' ')
	return lines

def add_title_and_explanation(img, title, explanation):
	title_font = ImageFont.truetype("arial.ttf", 24)
	exp_font = ImageFont.truetype("arial.ttf", 16)

	box_width, x_margin, y_margin, space_under_title, line_spacing = get_box_info()
	
	#get size of title text
	title_width = box_width - 2 * x_margin
	title_lines = split_text_into_lines(title, box_width, title_font)
	single_title_line_height = max([get_text_height(l, title_font) for l in title_lines])
	title_height = single_title_line_height * len(title_lines) + line_spacing * (len(title_lines) - 1)

	#get size of explanation text
	text_width = box_width - 2 * x_margin
	text_lines = split_text_into_lines(explanation, box_width, exp_font)
	single_exp_line_height = max([get_text_height(l, exp_font) for l in text_lines])
	#add  extra pixel of space between lines
	text_height = single_exp_line_height * len(text_lines) + line_spacing * (len(text_lines) - 1)

	box_height = 2 * y_margin + title_height + space_under_title + text_height

	#box is centered horizontally
	box_x = (RESX - box_width) // 2
	#box is at the bottom of the page
	box_y = EFFECTIVE_RESY - box_height

	poly = Image.new('RGBA', (box_width, box_height), "black")
	mask = Image.new(poly.mode, poly.size, (0,0,0,128))
	img.paste(poly, (box_x, box_y), mask)

	draw = ImageDraw.Draw(img)

	#cur_y keeps track of the y-coord to draw the next line
	cur_y = box_y + y_margin
	#draw title
	for line in title_lines:
		title_line_width = get_text_width(line, title_font)
		draw.text(((RESX - title_line_width) // 2, cur_y), line, (256,256,256), font=title_font)
		cur_y += single_title_line_height + line_spacing

	#extra space of line_spacing was added. Remove that and add the space under title
	cur_y = cur_y - line_spacing + space_under_title

	#draw explanation
	exp_x = box_x + x_margin
	for line in text_lines:
		draw.text((exp_x, cur_y), line, (256, 256, 256), font=exp_font)
		cur_y += single_exp_line_height + line_spacing

	return img

def prepare_image(old_fname, new_fname, title, explanation):
	img = Image.open(old_fname)
	img = resize_and_pad(img)
	img = add_title_and_explanation(img, title, explanation)
	img.save(new_fname)

#get various bits of info relating to the box
#maybe make this smarter?
def get_box_info():
	width = RESX // 2
	x_margin = 5
	y_margin = 5
	space_under_title = 20
	line_spacing = 2
	return width, x_margin, y_margin, space_under_title, line_spacing


h = get_html()
title = get_title(h)
explanation = get_explanation(h)
get_img(h)
prepare_image('temp.jpg', 'new.png', title, explanation)