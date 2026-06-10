import requests

class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def __send(self, path: str, method: str):
        return requests.request(method, self.base_url + path)

    def group_prefixes(self):
        """Возвращает список всех доступных префиксов групп."""
        """Вызывает groups.get_groupings() для получения всех группировок, извлекает их ключи и возвращает их в виде JSON-объекта по ключу 'prefixes'."""
        return self.__send(f'/group/prefixes', 'GET')

    def group(self, prefix: str):
        """Получает группы, соответствующие указанному префиксу."""
        """Выполняет поиск групп с заданным префиксом в базе данных, формирует список словарей, содержащих id и title, и возвращает этот список в формате JSON."""
        return self.__send(f'/group/{prefix}', 'GET')

    def variant_list(self):
        """Список всех вариантов."""
        """Возвращает список идентификаторов всех вариантов. Параметров не требуется."""
        return self.__send(f'/variant/list', 'GET')

    def task_list(self, gid: int, vid: int):
        """Получение списка задач по группе и варианту."""
        """Возвращает задачи, отфильтрованные указанным идентификатором группы и варианта. Параметры gid и vid должны быть целыми числами."""
        return self.__send(f'/group/{gid}/variant/{vid}/task/list', 'GET')

    def task(self, gid: int, vid: int, tid: int):
        """Получение статуса задачи."""
        """Возвращает текущий статус задачи, определённый идентификаторами группы, варианта и задачи. Принимает параметры gid, vid, tid."""
        return self.__send(f'/group/{gid}/variant/{vid}/task/{tid}', 'GET')

    def submit_task(self, gid: int, vid: int, tid: int):
        """Отправка ответа на задачу."""
        """Проверяет токен авторизации и изменяет статус задачи, принимая код ответа из тела запроса."""
        return self.__send(f'/group/{gid}/variant/{vid}/task/{tid}', 'POST')
