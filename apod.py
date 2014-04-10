import requests
import re
import shutil
from PIL import Image, ImageFont, ImageDraw
import textwrap

APOD = 'http://apod.nasa.gov/apod/ap140410.html'
APOD_BASE = 'http://apod.nasa.gov/apod/'
RESX = 1366
RESY = 768
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
		#no need to pad, just resize
		pass
	elif aspect_ratio < desired_aspect_ratio:
		resize_ratio = EFFECTIVE_RESY / height
		new_width = round(width * resize_ratio)
		new_height = EFFECTIVE_RESY
		img = img.resize((new_width, new_height), Image.ANTIALIAS)
		out_img = Image.new('RGB', (RESX, RESY), "black")
		out_img.paste(img, ((RESX - new_width)//2, 0))
	else:
		#pad on top and bottom
		pass
	return out_img

def add_title_and_explanation(img, title, explanation):
	box_width = RESX // 2
	box_height = 200
	x = (RESX - box_width) // 2
	y = EFFECTIVE_RESY - box_height
	poly = Image.new('RGBA', (box_width, box_height), "black")
	mask = Image.new(poly.mode, poly.size, (0,0,0,128))
	img.paste(poly, (x, y), mask)

	title_font = ImageFont.truetype("arial.ttf", 24)
	exp_font = ImageFont.truetype("arial.ttf", 16)
	draw = ImageDraw.Draw(img)

	#draw title
	title_width, title_height = draw.textsize(title, font=title_font)
	draw.text(((RESX - title_width) // 2, y + 5), title, (256,256,256), font=title_font)

	#draw explanation
	exp_x = x + 5
	exp_y = y + 20 + title_height
	lines = textwrap.wrap(explanation, MAX_LINE_LEN)
	for line in lines:
		w, h = exp_font.getsize(line)
		draw.text((exp_x, exp_y), line, (256, 256, 256), font=exp_font)
		exp_y += h
	return img


def prepare_image(old_fname, new_fname, title, explanation):
	img = Image.open(old_fname)
	img = resize_and_pad(img)
	img = add_title_and_explanation(img, title, explanation)
	img.save(new_fname)

h = get_html()
title = get_title(h)
explanation = get_explanation(h)
get_img(h)
prepare_image('temp.jpg', 'new.png', title, explanation)