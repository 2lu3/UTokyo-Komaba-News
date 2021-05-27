import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dotenv import load_dotenv
import psycopg2

# データベースを操作するクラス
class SQLDataBase:
    def __init__(self):
        self.dsn = os.environ["POSTGRES_URI"]
        self.table_name = "notifications"
        self.conn = None

    # データベースへ接続する関数
    # with ブロックで囲むため､あえてselfの変数に格納せず､return するようにしている
    def connect(self):
        return psycopg2.connect(self.dsn)

    # 前回お知らせしたタイトルをデータベースから読み出す
    def find_latest_notification(self):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f'SELECT * FROM {self.table_name}')
                rows = cur.fetchall()
                print('前回お知らせした内容:',rows[-1][0])
                return rows[-1][0]

    # 今回お知らせしたタイトルをデータベースに保存する
    def update_latest_notification(self, notification_title):
        with self.connect() as conn:
            with conn.cursor() as cur:
                # 一度データベースを削除
                cur.execute(f'DELETE FROM {self.table_name}')
                # データを保存
                cur.execute(f'INSERT INTO {self.table_name} VALUES (\'{notification_title}\')')


def post_to_line(title, url):
    ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"]
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    data = {
            "message": '新しいお知らせです!\n' + title + '\n' + url
            }
    requests.post(
            "https://notify-api.line.me/api/notify",
            headers=headers,
            data=data
            )

utokyo_notification_url = 'https://www.c.u-tokyo.ac.jp/zenki/news/kyoumu/index.html'
# 指定されたURLのHTMLをダウンロードして､BeautifulSoup オブジェクトを生成する
def create_soup():
    res = requests.get(utokyo_notification_url)
    return BeautifulSoup(res.text, 'html.parser')

# soupオブジェクトを受け取り､お知らせのリストを返す
def parse_into_notification_list(soup):
    definition_lists = soup.select('#newslist2 > dl')
    # 2021/05/27 時点では､'#newslist2 > dl'は1つ
    if len(definition_lists) != 1:
        return None

    definition_list = definition_lists[0]
    soup_notification_list = definition_list.find_all('a')
    notification_list = []
    for soup_notification in soup_notification_list:
        text = soup_notification.text
        url = urljoin(utokyo_notification_url, soup_notification.get('href'))
        notification_list.append([text, url])
    return notification_list


def main():
    load_dotenv()

    db = SQLDataBase()
    latest_notification_title = db.find_latest_notification()

    soup = create_soup()
    notification_list = parse_into_notification_list(soup)

    db.update_latest_notification(notification_list[0][0])
    for notification in notification_list:
        title = notification[0]
        url = notification[1]

        # 前回お知らせしたタイトルと同じ場合
        if title == latest_notification_title:
            print('これより前のお知らせは､前回お伝えしたものです')
            break

        post_to_line(title, url)
        print('posted', title, notification)

if __name__ == '__main__':
    main()


