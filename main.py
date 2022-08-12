import aiogram.utils.exceptions
import pyzoom.schemas

import config
import logging

import datetime
import database_handler
import input_handler
import re
from time import time
from aiogram import Bot, Dispatcher, executor, types
from pyzoom import ZoomClient

logging.basicConfig(level=logging.ERROR)
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(bot)

cache = {}
lesson_cache = {}


class School:
	def __init__(self, id, name):
		self.id = id
		self.name = name


class Lesson:
	def __init__(self, name, time, teacher, school, password, url, url_teacher):
		self.name = name
		self.time = time
		self.teacher = teacher
		self.school = school
		self.password = password
		self.url = url
		self.url_teacher = url_teacher


schools = [School("schoolInnopolis", "Лицей Иннополис")]
lessons = []


def inline(text, data):
	return types.InlineKeyboardButton(text=text, callback_data=data)


async def send_schedule(message, days_from_now_on):
	if days_from_now_on < 0:
		days_from_now_on = 0
	day_start = round(time()) - (round(time()) % 86400 - (86400 * days_from_now_on))
	day_end = round(time()) - (round(time()) % 86400 - (86400 * (days_from_now_on + 1)))
	when = "never"
	match days_from_now_on:
		case 0:
			when = "сегодня"
		case 1:
			when = "завтра"
		case 2:
			when = "послезавтра"
	if days_from_now_on > 2:
		when = f"через {days_from_now_on} дней(я)"
	msg = f"Занятия {when}:\n\n"
	filtered_list = []
	for lesson in lessons:
		if day_start <= lesson.time <= day_end:
			filtered_list.append(lesson)
	filtered_list = sorted(filtered_list, key=lambda x: x.time)
	if len(filtered_list) == 0:
		msg = f"❌ Занятий {when} нет."
	for i in filtered_list:
		msg += f"*{i.name}*\n" \
		           f"{datetime.datetime.fromtimestamp(i.time).strftime('%d.%m.%Y %H:%M')}\n" \
		           f"Проводит: {database_handler.get_user_name(i.teacher)}\n\n"
	PAGES = types.InlineKeyboardMarkup(row_width=2)
	buttons = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '1️⃣0️⃣']
	for i in range(len(filtered_list)):
		PAGES.add(inline(buttons[i], f"lesson_{days_from_now_on}_{i}"))
	PAGES.add(inline("◀️", f"schedule_{days_from_now_on - 1}"), inline("▶️", f"schedule_{days_from_now_on + 1}"))
	try:
		if 'заняти' in message.text.lower():
			await message.edit_text(msg, reply_markup=PAGES, parse_mode="markdown", disable_web_page_preview=True)
		else:
			await message.answer(msg, reply_markup=PAGES, parse_mode="markdown", disable_web_page_preview=True)
	except Exception as e:
		pass


def get_users_keyboard(call, page):
	days_from_now_on = int(call.data.split("_")[3])
	day_start = round(time()) - (round(time()) % 86400 - (86400 * days_from_now_on))
	day_end = round(time()) - (round(time()) % 86400 - (86400 * (days_from_now_on + 1)))
	filtered_list = []
	for lesson in lessons:
		if day_start <= lesson.time <= day_end:
			filtered_list.append(lesson)
	filtered_list = sorted(filtered_list, key=lambda x: x.time)
	lesson = filtered_list[int(call.data.split("_")[4])]
	if page < 0:
		page = 0
	if len(list(database_handler.get_all_users({'school': lesson.school, 'account_type': 'normal'}))) < (page + 1) * 5:
		page = len(list(database_handler.get_all_users({'school': lesson.school}))) // 5
	MENU = types.InlineKeyboardMarkup(row_width=2)
	counter = 0
	for i in database_handler.get_all_users({'school': lesson.school, 'account_type': 'normal'}):
		if counter == 5:
			return
		if i['_id'] in lesson_cache[lesson]['hands']:
			MENU.add(inline('🖐 ' + i['name'], "none"))
		else:
			MENU.add(inline(i['name'], "none"))
		counter += 1
	modified_data = '_'.join(call.data.split("_")[2:])
	MENU.add(inline("◀️", f"panel_{page - 1}_{modified_data}"),
	          inline("▶️", f"panel_{page + 1}_{modified_data}"))
	MENU.add(inline("⬅️ Назад", modified_data))
	return MENU


def generate_random_string(length: int):
	import random, string
	return ''.join(random.choice(string.ascii_letters + string.digits) for x in range(length))


def start_zoom_meeting(name, when, duration, api_key, api_secret):
	client = ZoomClient(api_key, api_secret)
	meeting = client.meetings.create_meeting(name, start_time=datetime.datetime.fromtimestamp(when).isoformat(), duration_min=duration,
	                               password=generate_random_string(10), settings=pyzoom.schemas.ZoomMeetingSettings(
						 host_video=True,
						 participant_video=True,
						 join_before_host=False,
						 mute_upon_entry=True,
						 approval_type=0,
						 cn_meeting=False,
						 in_meeting=False,
						 watermark=False,
						 use_pmi=False,
						 registration_type=1,
						 audio="voip",
						 auto_recording="none",
						 enforce_login=False,
						 waiting_room=False,
						 registrants_email_notification=False,
						 meeting_authentication=False,
						 contact_name="UFY",
						 contact_email="ufyit@support.com",
        ))
	return meeting


CANCEL_BUTTON = types.InlineKeyboardMarkup(row_width=2)
CANCEL_BUTTON.add(inline("❌ Отменить", "cancel"))


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
	if database_handler.exists(message.from_user.id):
		MENU = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
		if database_handler.get_user_group(message.from_user.id) == "teacher":
			MENU.add("📆 Расписание", "➕ Добавить занятие")
		else:
			MENU.add("📆 Расписание", "❓ Задать вопрос")
		await message.answer("Привет!", reply_markup=MENU)
		return
	await message.answer("Добро пожаловать! Чтобы получить доступ к боту, вам нужно зарегистрироваться. Если вы преподователь - напишите @quiulox с вашими ФИО, номером телефона, почтой и названием учебного заведения.")
	await message.answer("Введите ваше ФИО:", reply_markup=CANCEL_BUTTON)
	input_handler.wait_for(message.from_user.id, "userinfo_name")
	cache[message.from_user.id] = {}


@dp.message_handler()
async def message_handler(message: types.Message):
	if_waiting = input_handler.run_check(message.from_user.id)
	if if_waiting:
		match if_waiting:
			case "userinfo_name":
				cache[message.from_user.id]['name'] = message.text
				await message.answer("Введите вашу почту:", reply_markup=CANCEL_BUTTON)
				input_handler.wait_for(message.from_user.id, "userinfo_email")
			case "userinfo_email":
				if not re.search(".+@.+\..+", message.text):
					input_handler.wait_for(message.from_user.id, "userinfo_email")
					await message.answer(
						"Проверьте правильность ввода почты. Попробуйте снова:",
						reply_markup=CANCEL_BUTTON)
					return
				cache[message.from_user.id]['email'] = message.text
				await message.answer("Введите ваш телефон (в формате +7XXXXXXXXXX):", reply_markup=CANCEL_BUTTON)
				input_handler.wait_for(message.from_user.id, "userinfo_phone")
			case "userinfo_phone":
				if not re.search("\+7[0-9]{10}", message.text):
					input_handler.wait_for(message.from_user.id, "userinfo_phone")
					await message.answer(
						"Номер телефона должен быть в формате +7XXXXXXXXXX. Попробуйте снова:",
						reply_markup=CANCEL_BUTTON)
					return
				cache[message.from_user.id]['phone'] = message.text
				MENU = types.InlineKeyboardMarkup(row_width=1)
				for i in schools:
					MENU.add(inline(i.name, i.id))
				await message.answer("Выберите ваше учебное заведение:", reply_markup=MENU)
			case "addlesson_name":
				cache[message.from_user.id]['name'] = message.text
				await message.answer("Введите время занятия (формат DD.MM.YYYY HH:MM):", reply_markup=CANCEL_BUTTON)
				input_handler.wait_for(message.from_user.id, "addlesson_date")
			case "addlesson_date":
				if not re.search("[0-3][0-9].[0-1][0-9].[0-9]{4} [0-2][0-9]:[0-5][0-9]", message.text):
					input_handler.wait_for(message.from_user.id, "addlesson_date")
					await message.answer("Дата должна быть в формате DD.MM.YYYY HH:MM. Попробуйте снова:",
					                     reply_markup=CANCEL_BUTTON)
					return
				cache[message.from_user.id]['date'] = datetime.datetime.strptime(message.text, '%d.%m.%Y %H:%M').timestamp()
				await message.answer("Введите продолжительность занятия в минутах:", reply_markup=CANCEL_BUTTON)
				input_handler.wait_for(message.from_user.id, "addlesson_duration")
			case "addlesson_duration":
				try:
					int(message.text)
				except Exception as e:
					input_handler.wait_for(message.from_user.id, "addlesson_duration")
					await message.answer("Проверьте правильность ввода. Попробуйте снова:",
					                     reply_markup=CANCEL_BUTTON)
					return
				meeting = start_zoom_meeting(cache[message.from_user.id]['name'],
				                   cache[message.from_user.id]['date'],
				                   int(message.text),
				                   database_handler.get_user(message.from_user.id)['api_key'],
				                   database_handler.get_user(message.from_user.id)['api_secret']
				                   )
				database_handler.register_new_lesson(cache[message.from_user.id]['name'],
				                                     cache[message.from_user.id]['date'],
				                                     message.from_user.id,
				                                     database_handler.get_user_school(message.from_user.id),
							                   meeting.password,
							                   meeting.join_url,
							                   meeting.start_url)
				lessons.append(Lesson(cache[message.from_user.id]['name'],
				                      cache[message.from_user.id]['date'],
				                      message.from_user.id,
				                      database_handler.get_user_school(message.from_user.id),
				                      meeting.password,
				                      meeting.join_url,
				                      meeting.start_url))
				await message.answer("Занятие успешно создано!")
			case "question":
				await message.answer("Вы успешно задали вопрос!")
				await bot.send_message(int(cache[message.from_user.id]),
		                       f"Поступил вопрос от [{database_handler.get_user_name(message.from_user.id)}](tg://user?id={message.from_user.id}) (@{message.from_user.username}):\n\n{message.text}",
			                 parse_mode="markdown")
				cache.pop(message.from_user.id)
		return
	match message.text:
		case "📆 Расписание":
			await send_schedule(message, 0)
		case "❓ Задать вопрос":
			if database_handler.get_user_group(message.from_user.id) == "teacher":
				return
			MENU = types.InlineKeyboardMarkup(row_width=1)
			for i in database_handler.get_all_users({'account_type': 'teacher'}):
				MENU.add(inline(i['name'], i['_id']))
			await message.answer("Выберите преподователя:", reply_markup=MENU)
		case "➕ Добавить занятие":
			if database_handler.get_user_group(message.from_user.id) != "teacher":
				return
			await message.answer("Введите название занятия:", reply_markup=CANCEL_BUTTON)
			cache[message.from_user.id] = {}
			input_handler.wait_for(message.from_user.id, "addlesson_name")
		case "⏳ Зайти на занятие":
			if database_handler.get_user_group(message.from_user.id) != "teacher":
				return
			day_start = round(time()) - (round(time()) % 86400)
			day_end = round(time()) - (round(time()) % 86400 - -86400)
			msg = f"Занятия сегодня:\n\n"
			filtered_list = []
			for lesson in lessons:
				if day_start <= lesson.time <= day_end and lesson.teacher == message.from_user.id:
					filtered_list.append(lesson)
			filtered_list = sorted(filtered_list, key=lambda x: x.time)
			if len(filtered_list) == 0:
				msg = f"❌ Занятий сегодня нет."
			for i in filtered_list:
				url = i.url
				if database_handler.get_user_group(message.chat.id) == "teacher":
					url = i.url_teacher
				msg += f"[{i.name}]({url})\n" \
				       f"{datetime.datetime.fromtimestamp(i.time).strftime('%d.%m.%Y %H:%M')}\n"
		case _:
			await message.answer("Неизвестная команда!")


@dp.callback_query_handler()
async def callback_handler(call: types.CallbackQuery):
	if call.data.startswith("school"):
		for i in schools:
			if i.id == call.data:
				MENU = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
				MENU.add("📆 Расписание", "❓ Задать вопрос")
				await call.message.answer("Вы успешно зарегистрировались!", reply_markup=MENU)
				database_handler.register_new_user(call.from_user.id,
				                                   cache[call.from_user.id]['name'],
				                                   cache[call.from_user.id]['phone'],
				                                   cache[call.from_user.id]['email'],
				                                   call.data,
				                                   "normal")
				cache.pop(call.from_user.id)
		await call.answer()
		return
	if call.data.startswith("hand_"):
		days_from_now_on = int(call.data.split("_")[2])
		day_start = round(time()) - (round(time()) % 86400 - (86400 * days_from_now_on))
		day_end = round(time()) - (round(time()) % 86400 - (86400 * (days_from_now_on + 1)))
		filtered_list = []
		for lesson in lessons:
			if day_start <= lesson.time <= day_end:
				filtered_list.append(lesson)
		filtered_list = sorted(filtered_list, key=lambda x: x.time)
		lesson = filtered_list[int(call.data.split("_")[3])]
		if call.from_user.id in lesson_cache[lesson]['hands']:
			lesson_cache[lesson]['hands'].remove(call.from_user.id)
		else:
			lesson_cache[lesson]['hands'].append(call.from_user.id)
		call.data = '1_' + call.data
		for i in lesson_cache[lesson]['messages']:
			try:
				await i.edit_text(i.text, reply_markup=get_users_keyboard(call, 0))
			except Exception as e:
				pass
		await call.answer()
		return
	if call.data.startswith("schedule_"):
		await send_schedule(call.message, int(call.data.split("_")[1]))
		return
	if call.data.startswith("panel_"):
		days_from_now_on = int(call.data.split("_")[3])
		day_start = round(time()) - (round(time()) % 86400 - (86400 * days_from_now_on))
		day_end = round(time()) - (round(time()) % 86400 - (86400 * (days_from_now_on + 1)))
		filtered_list = []
		for lesson in lessons:
			if day_start <= lesson.time <= day_end:
				filtered_list.append(lesson)
		filtered_list = sorted(filtered_list, key=lambda x: x.time)
		lesson = filtered_list[int(call.data.split("_")[4])]
		if lesson not in lesson_cache:
			lesson_cache[lesson] = {'messages': [], 'hands': []}
		try:
			msg = await call.message.edit_text("Список учеников:", reply_markup=get_users_keyboard(call, int(call.data.split("_")[1])))
			lesson_cache[lesson]['messages'].append(msg)
		except aiogram.utils.exceptions.MessageNotModified as e:
			pass
		await call.answer()
		return
	if call.data.startswith("lesson_"):
		days_from_now_on = int(call.data.split("_")[1])
		day_start = round(time()) - (round(time()) % 86400 - (86400 * days_from_now_on))
		day_end = round(time()) - (round(time()) % 86400 - (86400 * (days_from_now_on + 1)))
		filtered_list = []
		for lesson in lessons:
			if day_start <= lesson.time <= day_end:
				filtered_list.append(lesson)
		filtered_list = sorted(filtered_list, key=lambda x: x.time)
		lesson = filtered_list[int(call.data.split("_")[2])]
		MENU = types.InlineKeyboardMarkup(row_width=1)
		url = lesson.url
		if database_handler.get_user_group(call.from_user.id) == "teacher":
			url = lesson.url_teacher
		MENU.add(types.InlineKeyboardButton("✅ Присоединиться", url=url))
		MENU.add(inline("👥️ Список учеников", f"panel_0_{call.data}"))
		if database_handler.get_user_group(call.from_user.id) != "teacher":
			MENU.add(inline("🖐 Поднять/опустить руку", "hand_" + call.data))
		MENU.add(inline("⬅️ Назад", "schedule_" + str(days_from_now_on)))
		if lesson in lesson_cache:
			for i in lesson_cache[lesson]['messages']:
				if i.chat.id == call.from_user.id:
					lesson_cache[lesson]['messages'].remove(i)
		await call.message.edit_text(f"Информация о занятии:\n"
		                          f"\n"
		                          f"Название: {lesson.name}\n"
		                          f"Время: {datetime.datetime.fromtimestamp(lesson.time).strftime('%d.%m.%Y %H:%M')}\n"
		                          f"Проводит: {database_handler.get_user_name(lesson.teacher)}", reply_markup=MENU)
		await call.answer()
		return
	match call.data:
		case "none":
			pass
		case "cancel":
			cache.pop(call.from_user.id)
			input_handler.cancel(call.from_user.id)
			await call.message.edit_text("Отменено.")
		case _:
			try:
				int(call.data)
				await call.message.answer("Введите ваш вопрос:", reply_markup=CANCEL_BUTTON)
				cache[call.from_user.id] = int(call.data)
				input_handler.wait_for(call.from_user.id, "question")
			except Exception as e:
				pass
	await call.answer()


async def on_startup(dp: Dispatcher):
	for i in database_handler.get_all_lessons():
		lessons.append(Lesson(i['name'], i['time'], i['teacher'], i['school'], i['password'], i['url'], i['url_teacher']))


executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
