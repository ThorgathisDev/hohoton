waiting_for = {}


def wait_for(user: int, for_: str):
	waiting_for[user] = for_


def run_check(user: int):
	if user in waiting_for.keys():
		for_ = waiting_for[user]
		waiting_for.pop(user)
		return for_
	return None


def cancel(user: int):
	waiting_for.pop(user)
