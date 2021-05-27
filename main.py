import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def create_message(notification):
    return '新しいお知らせです!\n' + notification[0] + '\n' + notification[1]
def post_to_line(message):
    ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"]
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    data = {
            "message": message
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
    soup = create_soup()
    notification_list = parse_into_notification_list(soup)
    for notification in notification_list:
        message = create_message(notification)
        post_to_line(message)
        exit()

if __name__ == '__main__':
    main()


