import requests
import pyfiglet
import json
import argparse
import os
from tqdm import tqdm
import re
import urllib.parse

# 读取请求头信息文件
from sympy.physics.units import time

with open('headers.txt', 'r') as file:
    headers_lines = file.readlines()

# 构造请求头
headers = {}
for line in headers_lines:
    key, value = line.strip().split(': ', 1)
    headers[key] = value

host = 'https://www.yuque.com'
MAX_RETRIES = 3  # 设置最大重试次数
failed_docs = []  # 存储失败的文档信息

# 获取个人账号下知识库列表，包括slug，user.login
def get_book_stacks():
    response = requests.get(host + "/api/mine/book_stacks", headers=headers)
    if response.status_code == 200:
        book_stacks_data = response.json().get("data", [])
        book_info = []
        for stack in book_stacks_data:
            books = stack.get("books", [])
            for book in books:
                book_id = book.get("id")
                book_name = book.get("name")
                book_slug = book.get("slug")
                user_login = book.get("user").get("login")
                book_info.append({"id": book_id, "name": book_name, "slug": book_slug, "login": user_login})
        return book_info
    else:
        print("获取失败QAQ")
        return None


# 获取特定知识库下的文章列表,根据book_id找到对应路径
def get_docs(book_id,book_stacks,file_path):
    book_path=''
    for book_stack in book_stacks:
        id = book_stack['id']
        slug = book_stack['slug']
        login = book_stack['login']
        if book_id==id:
            book_path=login+"/"+slug
            print(book_path)
            break

    response = requests.get(host + f"/r/{book_path}/toc", headers=headers)
    if response.status_code == 200:
        html_content = response.text

        # 使用正则表达式匹配 JavaScript 数据
        pattern = re.compile(r'window.appData = JSON.parse\(decodeURIComponent\("([^"]+)"\)\);', re.DOTALL)
        match = pattern.search(html_content)
        if match:
            encoded_data = match.group(1)
            # 解码并处理获取的内容
            decoded_data = urllib.parse.unquote(encoded_data)
            # 在这里可以将 JSON 解析为 Python 对象
            json_data = json.loads(decoded_data)
            book_data = json_data.get("book")
            doc_list = book_data.get("toc")
            download_documents_tree(doc_list,file_path)
        else:
            print("No match found")
        return
    else:
        print(f"知识库获取失败QAQ Book ID: {book_id}")
        return None

# 根据toc目录结构和文档信息获取下载链接并下载文档
def download_documents_tree(document_info, file_path):
    # 创建一个字典，用于按层级组织标题和文档
    hierarchy = {'': []}  # 为顶级标题创建一个占位键
    for info in document_info:
        type = info['type']
        title = info['title']
        uuid = info['uuid']
        parent_uuid = info['parent_uuid']
        child_uuid = info['child_uuid']
        doc_id = info['doc_id']
        level = info['level']

        if type == "TITLE":
            # 在层级字典中创建一个空列表，用于存储该层级的内容
            hierarchy[uuid] = []

        # 将文档信息放入对应层级的列表中
        hierarchy[parent_uuid].append(info)

    # 根据字典构建正确的目录结构和下载文档
    def traverse_hierarchy(parent_uuid, current_path):
        for info in hierarchy.get(parent_uuid, []):
            type = info['type']
            title = info['title']
            uuid = info['uuid']
            child_uuid = info['child_uuid']

            if type == "TITLE":
                # 如果是标题，创建文件夹并继续递归处理子级
                folder_path = os.path.join(current_path, title)
                os.makedirs(folder_path, exist_ok=True)
                traverse_hierarchy(uuid, folder_path)
            elif type == "DOC":
                # 如果是文档，下载文档到当前路径
                doc_id = info['doc_id']
                download_link = get_doc_download_link(doc_id,title)
                if download_link:
                    download_file(download_link, title, current_path)

    # 从顶级开始遍历层级字典，构建正确的目录结构
    traverse_hierarchy('', file_path)

# 获取文档下载链接
def get_doc_download_link(doc_id,doc_title):
    retries = 0
    download_link = None

    while retries < MAX_RETRIES and not download_link:
        # 构造请求体数据
        payload = {"type": "word", "force": 0}
        # 转换为 JSON 格式
        json_payload = json.dumps(payload)

        export_url = host + f"/api/docs/{doc_id}/export"
        response = requests.post(export_url, headers=headers, data=json_payload)

        if response.status_code == 200:
            data = response.json().get("data")
            download_link = data.get("url")
        else:
            # 导出失败，重试几次
            print(f"获取下载链接失败: {doc_id}. Retrying...")
            retries += 1
    if not download_link:
        message = response.json().get("message")
        print(message)
        failed_docs.append({"doc_id": doc_id,"title":doc_title,"reason": message})
    return download_link


# 下载文档
def download_file(url, title, path):
    # title过滤特殊字符
    cleaned_title = re.sub(r'[\\/:*?"<>|]', '', title)
    # 组合路径和文件名
    file_path = os.path.join(path, f"{cleaned_title}.docx")
    if os.path.exists(file_path):
        print(f"File {file_path} already exists. Overwriting...")
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        total_size = int(response.headers.get('content-length', 0))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as file, tqdm(
                desc=file_path,
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                ascii=True,
                miniters=1,
                colour='green',
        ) as progress_bar:
            for data in response.iter_content(chunk_size=4096):
                file.write(data)
                progress_bar.update(len(data))
        print(f"下载成功^^")
    else:
        print("下载失败QAQ")


def generate_banner(script_name):
    ascii_banner = pyfiglet.figlet_format(script_name)
    print(ascii_banner + "v2.0")
    print("欢迎使用YuQueDocFetch~")
    print("INFO:")
    print("  -p 指定文档下载路径(默认./output/)，示例：python YuQueDocFetch.py -p ./output/ \n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-p', '--path', default='./output/', help='文档的保存路径')
    args = parser.parse_args()
    file_path = args.path

    script_name = "YuQueDocFetch"
    generate_banner(script_name)
    # 输出知识库列表
    book_stacks = get_book_stacks()
    if book_stacks:
        book_count = 0
        # 输出知识库列表
        print("知识库列表:")
        for book_stack in book_stacks:
            print(f"Book ID: {book_stack['id']}, Name: {book_stack['name']}")
            book_count += 1
        print("Row: " + str(book_count))

        # 根据输出的知识库列表选择输入一个book_id
        while True:
            selected_book_id = input("请输入您要查询的知识库ID: ")

            # 校验输入的book_id是否在列表中
            book_ids = [stack['id'] for stack in book_stacks]
            if selected_book_id.isdigit() and int(selected_book_id) in book_ids:
                print(f"已选中 Book ID: {selected_book_id}, 文档下载中……")
                # 在这里继续处理选定的 book_id
                break  # 输入有效，跳出循环
            else:
                print("您输入的ID不在列表中，请重新输入")
        get_docs(int(selected_book_id),book_stacks,file_path)
        if failed_docs:
            print("Error Download Doc Info: ")
            for error in failed_docs:
                error_doc_id = error['doc_id']
                error_doc_title = error['title']
                error_reason = error['reason']
                print("Doc ID: " + str(error_doc_id) + ", Title: " + error_doc_title + ", Reason: " + error_reason)
        else:
            print("全部下载成功~")

    else:
        print("No book found")