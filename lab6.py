import os
import logging
from functools import wraps
import xml.etree.ElementTree as ET
from xml.dom import minidom


class FileNotFound(Exception):
    def __init__(self, filepath):
        super().__init__(f"Файл не знайдено: {filepath}")


class FileCorrupted(Exception):
    def __init__(self, filepath, reason=""):
        super().__init__(f"Файл пошкоджено: {filepath}. {reason}")


def logged(exception, mode="console"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__name__)
            logger.setLevel(logging.INFO)
            logger.handlers = []
            
            if mode == "file":
                handler = logging.FileHandler("operations.log", encoding='utf-8')
            else:
                handler = logging.StreamHandler()
            
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
            try:
                logger.info(f"Початок: {func.__name__}")
                result = func(*args, **kwargs)
                logger.info(f"Успіх: {func.__name__}")
                return result
            except exception as e:
                logger.error(f"Помилка: {str(e)}")
                raise
        return wrapper
    return decorator


class XMLFile:
    def __init__(self, filepath):
        self.filepath = filepath
        if not os.path.exists(filepath):
            raise FileNotFound(filepath)
    
    @logged(FileCorrupted, mode="console")
    def read(self):
        try:
            tree = ET.parse(self.filepath)
            return self._to_dict(tree.getroot())
        except ET.ParseError:
            raise FileCorrupted(self.filepath, "Невірний XML")
        except PermissionError:
            raise FileCorrupted(self.filepath, "Немає доступу")
    
    @logged(FileCorrupted, mode="file")
    def write(self, data):
        try:
            root = ET.Element("data")
            self._from_dict(root, data)
            xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write(xml_str)
        except PermissionError:
            raise FileCorrupted(self.filepath, "Немає доступу")
    
    @logged(FileCorrupted, mode="file")
    def append(self, data):
        try:
            tree = ET.parse(self.filepath)
            root = tree.getroot()
            item = ET.SubElement(root, "item")
            self._from_dict(item, data)
            xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write(xml_str)
        except ET.ParseError:
            raise FileCorrupted(self.filepath, "Невірний XML")
    
    def _to_dict(self, elem):
        result = {}
        if elem.text and elem.text.strip():
            if len(elem) == 0:
                return elem.text.strip()
        for child in elem:
            data = self._to_dict(child)
            if child.tag in result:
                if type(result[child.tag]) != list:
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(data)
            else:
                result[child.tag] = data
        return result if result else None
    
    def _from_dict(self, parent, data):
        if type(data) == dict:
            for key, val in data.items():
                if type(val) == list:
                    for item in val:
                        child = ET.SubElement(parent, key)
                        self._from_dict(child, item)
                else:
                    child = ET.SubElement(parent, key)
                    self._from_dict(child, val)
        else:
            parent.text = str(data)


if __name__ == "__main__":
    filepath = "data.xml"
    
    root = ET.Element('data')
    for name, grade in [('Іван', '5'), ('Марія', '4')]:
        s = ET.SubElement(root, 'student')
        ET.SubElement(s, 'name').text = name
        ET.SubElement(s, 'grade').text = grade
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(minidom.parseString(ET.tostring(root)).toprettyxml(indent="  "))
    
    print("Файл створено")
    
    try:
        handler = XMLFile(filepath)
        print("\nЧитання:")
        print(handler.read())
        
        print("\nЗапис:")
        handler.write({'name': 'Петро', 'grade': '5'})
        print(handler.read())
        
        print("\nДописування:")
        handler.append({'name': 'Ольга', 'grade': '4'})
        print(handler.read())
        
    except FileNotFound as e:
        print(f"Помилка: {e}")
    except FileCorrupted as e:
        print(f"Помилка: {e}")
    
    print("\nТест неіснуючого файлу:")
    try:
        XMLFile("none.xml")
    except FileNotFound as e:
        print(f"Оброблено: {e}")