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


class FireBaseManager:
    def __init__(self):
        load_dotenv(verbose=False)
        firebase_admin.initialize_app()
        self.db = firestore.client()
        self.notification_ref = self.db.collection(u'notification')

    def delete_oldest_notifications(self, number=1):
        # query = self.notification_ref.order_by(
        # 'timestamp', direction = firestore.Query.DESCENDING).limit(number)
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

    def get_titles(self):
        title_list = []
        for notification in self.notification_ref.stream():
            title_list.append(notification.to_dict()["title"])
        return title_list


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


def get_notification_title_list():
    utokyo_notification_url = 'http://www.c.u-tokyo.ac.jp/zenki/news/kyoumu/index.html'

    # 指定されたURLのHTMLをダウンロードして､BeautifulSoup オブジェクトを生成する
    res = requests.get(utokyo_notification_url)
    soup = BeautifulSoup(res.text, 'html.parser')

    print(soup)
    definition_lists = soup.select('#newslist2 > dl')
    # 2021/05/27 時点では､'#newslist2 > dl'は1つ
    print(definition_lists)
    if len(definition_lists) != 1:
        return None

    definition_list = definition_lists[0]

    # 通知のsoupオブジェクト
    soup_notification_list = definition_list.find_all('a')

    notification_list = []
    for soup_notification in soup_notification_list:
        text = soup_notification.text
        url = urljoin(utokyo_notification_url,
                      soup_notification.get('href'))
        notification_list.append([text, url])
    return notification_list


def main():
    load_dotenv()

    firebase = FireBaseManager()
    # firebase.delete_all()

    # [[title, url], [title, url], [title url]]
    homepage_notification_list = get_notification_title_list()
    assert homepage_notification_list is not None

    print('homepage notifications')
    print(homepage_notification_list)

    # [title, title, title]
    database_notifications = firebase.get_titles()
    print('database titles')
    print(database_notifications)

    # まだ通知されていないリスト
    un_notified_list = []
    for new_title, new_url in homepage_notification_list:
        if not new_title in database_notifications:
            un_notified_list.append([new_title, new_url])
        else:
            # 以前通知したメッセージが見つかった時点で、探索を終わる
            break

    # 古い順に通知を送る
    un_notified_list = un_notified_list[::-1]
    for title, url in un_notified_list:
        print(f'sending {title}')
        send2line(title, url)
        firebase.add_notification(title)
        time.sleep(1)

    print('title num', len(firebase.get_titles()))
    delete_news_num = len(firebase.get_titles()) - 500
    print('delete num', delete_news_num)

    if delete_news_num > 0:
        firebase.delete_oldest_notifications(delete_news_num)


if __name__ == '__main__':
    main()
