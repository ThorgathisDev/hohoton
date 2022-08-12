from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['hohloton']


def exists(user_id: int):
	return db['users'].find_one({'_id': user_id}) is not None


def register_new_user(user_id: int, name: str, phone: str, email: str, school: str, account_type: str, api_key=None, api_secret=None):
	document = {'_id': user_id, 'name': name, 'phone': phone, 'email': email, 'school': school,
	            'account_type': account_type, 'api_key': api_key, 'api_secret': api_secret}
	return db['users'].insert_one(document)


def register_new_lesson(name: str, time: int, teacher: str, school: str, password: str, url: str, url_teacher: str):
	document = {'name': name, 'time': time, 'teacher': teacher, 'school': school,
	            'password': password, 'url': url, 'url_teacher': url_teacher}
	return db['lessons'].insert_one(document)


def get_user(user_id: int):
	return db['users'].find_one({'_id': user_id})


def get_user_group(user_id: int):
	return db['users'].find_one({'_id': user_id})['account_type']


def get_user_name(user_id: int):
	return db['users'].find_one({'_id': user_id})['name']


def get_user_school(user_id: int):
	return db['users'].find_one({'_id': user_id})['school']


def get_all_lessons(filter_=None):
	if filter_ is None:
		filter_ = {}
	return db['lessons'].find(filter_)


def get_all_users(filter_=None):
	if filter_ is None:
		filter_ = {}
	return db['users'].find(filter_)
