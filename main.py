import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import firestore
from datetime import datetime
from typing import Optional
import time

log_file_name = "/home/tlaloc/log/titles.log"
def read_all_titles():
    if not os.path.exists(log_file_name):
        print('log file not found')
        return []
    with open(log_file_name, 'r') as f:
        return f.read().splitlines()

def save_all_titles(titles):
    with open(log_file_name, 'w') as f:
        for title in titles:
            f.write(title)
            f.write('\n')

def send2line(title, url):
    load_dotenv()
    LINE_ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"]
    headers = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}"}
    data = {
        "message": '新しいお知らせです!\n' + title + '\n' + url
    }
    requests.post(
        "https://notify-api.line.me/api/notify",
        headers=headers,
        data=data
    )


def get_homepage_notification_titles():
    utokyo_notification_url = 'http://www.c.u-tokyo.ac.jp/zenki/news/kyoumu/index.html'

    # 指定されたURLのHTMLをダウンロードして､BeautifulSoup オブジェクトを生成する
    res = requests.get(utokyo_notification_url)
    soup = BeautifulSoup(res.text, 'html.parser')

    definition_lists = soup.select('#newslist2 > dl')
    # 2021/05/27 時点では､'#newslist2 > dl'は1つ
    print('definition_lists num ', len(definition_lists))
    if len(definition_lists) != 1:
        print("error definition_lists != 1")
        print(soup)
        print(definition_lists)
        return None, None

    definition_list = definition_lists[0]

    # 通知のsoupオブジェクト
    soup_notification_list = definition_list.find_all('a')

    title_list = []
    url_list = []
    for soup_notification in soup_notification_list:
        text = soup_notification.text
        url = urljoin(utokyo_notification_url,
                      soup_notification.get('href'))
        title_list.append(text)
        url_list.append(url)
    return title_list, url_list


def main():
    print("utokyo notify app start", datetime.now())
    load_dotenv()


    # [[title, url], [title, url], [title url]]
    homepage_title_list, homepage_url_list = get_homepage_notification_titles()
    assert homepage_title_list is not None
    assert homepage_url_list is not None

    # [title, title, title, ...]
    saved_notifications = read_all_titles()
    print('\n\n\n')
    print('saved titles')
    [print(title) for title in saved_notifications]
    print('\n\n\n')
    print('homepage titles')
    [print(title) for title in homepage_title_list]
    save_all_titles(homepage_title_list)

    # まだ通知されていないリスト
    un_notified_list = []
    print('un_notified_list')
    print('\n\n\n')
    for new_title, new_url in zip(homepage_title_list, homepage_url_list):
        if not new_title in saved_notifications:
            print(new_title)
            un_notified_list.append([new_title, new_url])
        else:
            # 以前通知したメッセージが見つかった時点で、探索を終わる
            break

    # 古い順に通知を送る
    un_notified_list = un_notified_list[::-1]

    print('\n\n\n')
    if len(un_notified_list) > 5:
        send2line(str(len(un_notified_list)) + '件の通知が送信されようとしています', '@武藤ひかる エラーか確認してください')
        return
    else:
        for title, url in un_notified_list:
            print(f'sending {title}')
            send2line(title, url)
            time.sleep(3)




if __name__ == '__main__':
    main()

class FireBaseManager:
    def __init__(self):
        load_dotenv(verbose=False)
        firebase_admin.initialize_app()
        self.db = firestore.client()
        self.notification_ref = self.db.collection(u'notification')
        self.titles = []
        self.read_titles()

    def delete_oldest_notifications(self, number=1):
        query = self.notification_ref.order_by(
            'timestamp').limit_to_last(number)
        docs = query.get()
        for doc in docs:
            print(doc.to_dict()["title"])
            doc.reference.delete()

    def delete_all(self):
        docs = self.notification_ref.stream()

        for doc in docs:
            doc.reference.delete()

    def add_notification(self, title: str):
        self.notification_ref.add({
            u"title": title,
            u"timestamp": firestore.SERVER_TIMESTAMP
        })

    def read_titles(self):
        self.titles = []
        for notification in self.notification_ref.stream():
            self.titles.append(notification.to_dict()["title"])

    def get_titles(self):
        return self.titles
