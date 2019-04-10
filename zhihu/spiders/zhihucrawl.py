# -*- coding: utf-8 -*-
import base64
import scrapy
import pickle
import time
from selenium import webdriver
from scrapy.loader import ItemLoader
from urllib import parse
from selenium.webdriver.common.keys import Keys
from zhihu.items import ZhihuItemQuestion, ZhihuItemAnswer
from selenium.webdriver.chrome.options import Options
import re
import json
import datetime
from scrapy.selector import Selector
from mouse import move, click
import os
from utils.common import captcha_inverted_cn
from utils.common import yundama_captcha


class ZhihucrawlSpider(scrapy.Spider):
    name = 'zhihucrawl'
    allowed_domains = ['www.zhihu.com']
    KEY_WORD = input("输入知乎搜索关键字：")
    start_url = ["https://www.zhihu.com/search?q={0}".format(KEY_WORD)]
    start_answer_url = "https://www.zhihu.com/api/v4/questions/{0}/answers?include=data%5B%2A%5D.is_normal%2Cadmin_closed_comment%2Creward_info%2Cis_collapsed%2Cannotation_action%2Cannotation_detail%2Ccollapse_reason%2Cis_sticky%2Ccollapsed_by%2Csuggest_edit%2Ccomment_count%2Ccan_comment%2Ccontent%2Ceditable_content%2Cvoteup_count%2Creshipment_settings%2Ccomment_permission%2Ccreated_time%2Cupdated_time%2Creview_info%2Crelevant_info%2Cquestion%2Cexcerpt%2Crelationship.is_authorized%2Cis_author%2Cvoting%2Cis_thanked%2Cis_nothelp%2Cis_labeled%3Bdata%5B%2A%5D.mark_infos%5B%2A%5D.url%3Bdata%5B%2A%5D.author.follower_count%2Cbadge%5B%2A%5D.topics&limit={1}&offset={2}&platform=desktop&sort_by=default"

    def start_requests(self):
        if os.path.exists("D:/PythonProjects/zhihu/cookies/zhihu.cookie"):
            cookies = pickle.load(open('D:/PythonProjects/zhihu/cookies/zhihu.cookie', 'rb'))
            return [scrapy.Request(url=self.start_url[0], dont_filter=True, cookies=cookies)]
        else:
            chrome_options = Options()
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            browser = webdriver.Chrome(executable_path="D:/Evns/py3scrapy/Scripts/chromedriver.exe", chrome_options=chrome_options)
            browser.get("https://www.zhihu.com/signin")
            browser.find_element_by_css_selector(".SignFlow-accountInput.Input-wrapper input").send_keys(Keys.CONTROL + 'a')
            browser.find_element_by_css_selector(".SignFlow-accountInput.Input-wrapper input").send_keys("13169188007")
            browser.find_element_by_css_selector(".SignFlow-password input").send_keys(Keys.CONTROL + 'a')
            browser.find_element_by_css_selector(".SignFlow-password input").send_keys("lyg960926")
            move(675, 508)
            click()
            time.sleep(1.5)
            login_status = False
            while login_status:
                try:
                    browser.find_element_by_css_selector(".Popover.AppHeader-menu")
                    login_status = True
                except:
                    try:
                        # 判断是否是英文验证码，并识别图片返回验证码，并提交
                        captcha_en_img = browser.find_element_by_xpath("//div[@class='Captcha-chineseContainer']/img/@src")
                        img = (re.match('.*base64,(R.*)', captcha_en_img, re.S)).group(1)
                        with open("D:PythonProjects/zhihu/utils/en_captcha.png", "wb") as f:
                            f.write(base64.b64decode(img))
                        en_captcha = yundama_captcha("D:PythonProjects/zhihu/utils/en_captcha.png")
                    except:
                        # 判断是否中文验证码，并识别图片验证码返回倒立文字坐标，利用坐标模拟点击倒立文字
                        captcha_cn_img = browser.find_element_by_css_selector("//div[@class='Captcha-englishContainer']/img/@src")
                        img = (re.match('.*base64,(R.*)', captcha_cn_img, re.S)).group(1)
                        with open("D:PythonProjects/zhihu/utils/cn_captcha.gif", "wb") as f:
                            f.write(base64.b64decode(img))
                        cn_captcha = captcha_inverted_cn("D:PythonProjects/zhihu/utils/cn_captcha.gif")

            cookies = browser.get_cookies()
            cookie_dict = {}
            for cookie in cookies:
                with open('D:/PythonProjects/zhihu/cookies/zhihu.cookie', 'wb')as f:
                    pickle.dump(cookie, f)
                cookie_dict[cookie['name']] = cookie['value']
            return [scrapy.Request(url=self.start_url[0], dont_filter=True, encoding="utf-8", cookies=cookie_dict)]

    def parse(self, response):
        browser = webdriver.Chrome(executable_path="D:/Evns/py3scrapy/Scripts/chromedriver.exe")
        browser.get(response.url)
        for i in range(20):
            browser.execute_script(
                "window.scrollTo(0, document.body.scrollHeight); var lenOfPage=document.body.scrollHeight; return lenOfPage;")
            time.sleep(1)
        selector = Selector(text=browser.page_source)
        browser.quit()
        all_urls = selector.xpath("//div[@itemprop='zhihu:question']//a/@href").extract()
        all_urls = [parse.urljoin('https://www.zhihu.com', url) for url in all_urls]
        all_urls = filter(lambda x: True if x.startswith("https") else False, all_urls)
        for url in all_urls:
            match_url = re.match('(.*zhihu.com/question/(\d+))(/|$).*', url)
            if match_url:
                question_url = match_url.group(1)
                question_id = match_url.group(2)
                print(question_url, question_id)
                yield scrapy.Request(url=question_url, meta={"question_id": question_id}, callback=self.parse_question)
            else:
                yield scrapy.Request(url=url, callback=self.parse)

    def parse_question(self, response):
        item_loader = ItemLoader(item=ZhihuItemQuestion(), response=response)
        item_loader.add_value("zhihu_id", response.meta.get("question_id"))
        item_loader.add_value("url", response.url)
        item_loader.add_xpath("title", "//h1[@class='QuestionHeader-title']//text()")
        try:
            item_loader.add_xpath("main_content", "//div[@class='QuestionHeader-detail']//text()")
        except:
            item_loader.add_value("main_content", "无详细内容")
        item_loader.add_xpath("tag", "//div[@class='QuestionHeader-topics']//text()")
        item_loader.add_xpath("focus_num", "//div[@class='NumberBoard-item'][1]//strong[@class='NumberBoard-itemValue']/text()")
        item_loader.add_xpath("click_num", "//div[@class='NumberBoard-item']//strong//text()")
        item_loader.add_xpath("comment_num", "normalize-space(//div[@class='QuestionHeader-Comment']/button/text()[1])")
        item_loader.add_xpath("answer_num", "normalize-space(//div[@class='List-header']//span//text()[1])")

        question_item = item_loader.load_item()

        yield scrapy.Request(url=self.start_answer_url.format(response.meta.get("question_id"), 20, 0),
                             callback=self.parse_answer)
        yield question_item

    def parse_answer(self, response):
        answer_json = json.loads(response.text)
        is_end = answer_json["paging"]["is_end"]
        next_url = answer_json["paging"]["next"]

        for answer in answer_json["data"]:
            answer_item = ZhihuItemAnswer()
            answer_item["answer_id"] = answer["id"]
            answer_item["url"] = answer["url"]
            answer_item["question_id"] = answer["question"]["id"]
            answer_item["author"] = answer["author"]["name"] if "name" in answer["author"] else None
            answer_item["main_content"] = answer["content"] if "content" in answer else answer["excerpt"]
            answer_item["praise_num"] = answer["voteup_count"]
            answer_item["comments_num"] = answer["comment_count"]
            answer_item["update_time"] = answer["updated_time"]
            answer_item["create_time"] = answer["created_time"]
            answer_item["crawl_time"] = datetime.datetime.now()

            yield answer_item
        if not is_end:
            yield scrapy.Request(url=next_url, callback=self.parse_answer)
