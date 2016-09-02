# -*- coding:utf-8 -*-
from lxml import etree
import requests
import os
import sys
import MySQLdb
import re
reload(sys)
sys.setdefaultencoding("utf-8")

#获取网页源码
def getsource(url):
    html = requests.get(url)
    html.encoding = 'utf-8'
    return html.text

#获取信息块
def getcountryblock(source):
    blocks = re.findall('(<h3 class="title fontYaHei".*?</h3>)',source,re.S)
    return blocks

#获取信息块
def getpoiblock(source):
    blocks = re.findall('(<li class="clearfix".*?</li>)',source,re.S)
    return blocks

# 对匹配为空的内容进行处理
def pankong(poi_xx):
    if len(poi_xx)==0:
        poi_xx = ''
    else:
        poi_xx = poi_xx[0]
    return poi_xx

if __name__ == '__main__':
    country = 'singapore'
    city = '新加坡'
    starturl = 'http://place.qyer.com/singapore/'

    db = 'test'
    # 数据表
    tb = 'map_poi'
    hulvcities = range(1,998)

    try:
		# 连接数据库
        conn = MySQLdb.connect(host='127.0.0.1', user='root', passwd='', port=3306, charset='utf8')
       
        cur = conn.cursor()
        cur.execute('set interactive_timeout=96*3600')
        conn.select_db(db)
    except MySQLdb.Error, e:
        print "Mysql Error %d: %s" % (e.args[0], e.args[1])
	
    if 999 in hulvcities:
        print city, 'alread，ignore。。'
        pass
    else:
        # 城市主页
        sighturl = starturl+'sight/'
        foodurl = starturl+'food/'
        shoppingurl = starturl+'shopping/'
        city_urls = [sighturl,foodurl,shoppingurl]
        for ci,cityurl in enumerate(city_urls):
            print cityurl
            sub_html = getsource(cityurl)
            sub_selector = etree.HTML(sub_html)
            # 爬取的页数
            poi_page_num = sub_selector.xpath('//div[@class="ui_page"]/a/@data-page')
            try:
                poi_page_num = poi_page_num[-2]
            except:
                pass
            else:
                for poi_page in range(1,int(poi_page_num)+1):
                    current_url = cityurl+"?page=%s"%(poi_page)
                    print 'url in url_list_page',current_url
                    current_html = getsource(current_url)
                    poiblocks = getpoiblock(current_html)
                    print 'poi_count in current_page',len(poiblocks)
                    for poiblock in poiblocks:
                        current_selector = etree.HTML(poiblock)

                        # 中文、英文、本地名称
                        name0 = current_selector.xpath('//h3[@class="title fontYaHei"]/a/text()')[0].strip()
                        name1 = current_selector.xpath('//h3[@class="title fontYaHei"]/a/span/text()')
                        if len(name1)==0:
                            name1 = ''
                        else:
                            name1 = name1[0].strip()

                        first_issue = name0[0].encode('utf-8')
                        if first_issue.isalpha():
                            poi_en_name = name0
                            poi_ch_name = ''
                        else:
                            poi_en_name = name1
                            poi_ch_name = name0
                        poi_loc_name = poi_en_name

                        # 类别id
                        if ci == 0:
                            tag_id = 3
                        elif ci == 1:
                            tag_id =1
                        elif ci == 2:
                            tag_id = 4
                        # 评分
                        poi_score = current_selector.xpath('//span[@class="grade"]/text()')
                        if len(poi_score)==0:
                            poi_score=''
                        else:
                            poi_score = poi_score[0]

                        # 排名
                        poi_rank = current_selector.xpath('//em[@class="rank orange"]/text()')
                        poi_rank = pankong(poi_rank)
                        newstr = ''
                        for sr in poi_rank:
                            if sr.isdigit():
                                newstr = newstr + sr
                        poi_rank = newstr

                        # 详情页url
                        detail_url = current_selector.xpath('//h3[@class="title fontYaHei"]/a/@href')[0]
                        print 'detail page',detail_url
                        try:
                            detail_html = getsource(detail_url)
                        except:
                            pass
                        else:
                            detail_selector = etree.HTML(detail_html)
                            poi_tips_title = detail_selector.xpath('//div[@class="poiDet-main"]/ul[@class="poiDet-tips"]/li/span/text()')
                            title_list = []
                            for tipi,title in enumerate(poi_tips_title):
                                title = title.strip()
                                title_list.append(title)

                            for ti,title in enumerate(title_list):
                                if title =='':
                                    title_list.pop(ti)
                            for bi,title in enumerate(title_list):
                                if title == '地址：':
                                    addi = bi + 1
                                if title == '电话：':
                                    telei = bi + 1
                            if '地址：'in title_list:
                                # 地址
                                xpath_str_add = "//ul[@class='poiDet-tips']/li["+str(addi)+"]/div/p/text()"
                                poi_address = detail_selector.xpath(xpath_str_add)
                                poi_address = pankong(poi_address)
                            else:
                                poi_address = ''

                            if '电话：'in title_list:
                                # 电话
                                xpath_str_tele = "//ul[@class='poiDet-tips']/li[" + str(telei) + "]/div/p/text()"
                                poi_telephone = detail_selector.xpath(xpath_str_tele)
                                poi_telephone = pankong(poi_telephone)
                                if not poi_telephone:
                                    poi_telephone = ''
                            else:
                                poi_telephone = ''
                            # 评论数
                            comments = current_selector.xpath('//div[@class="info"]/span[@class="dping"]/a/text()')
                            if len(comments)==0:
                                comments =''
                            else:
                                comments = comments[0]

                            comments_count = comments.strip()
                            newstr1 = ''
                            for sr1 in comments_count:
                                if sr1.isdigit():
                                    newstr1 = newstr1 + sr1
                            comments_count = newstr1
                            # 来源
                            source = 'qyer'
                            sqli = "INSERT INTO " + db + "." + tb + "(poi_ch_name,poi_en_name,poi_loc_name,poi_tag_id,poi_score,poi_rank,poi_address,poi_telephone,comments_count,source_website)" + " VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"

                            # 判断数据库是否已经存在城市数据，决定是插入数据还是更新数据。
                            sqli1 = "select * from " + db + "." + tb + " where poi_ch_name = " + "'%s'" % (poi_ch_name)
                            sqli2 = "select * from " + db + "." + tb + " where poi_en_name = " + "'%s'" % (poi_en_name)
                          
                            try:
                                r1 = cur.execute(sqli1)
                                r2 = cur.execute(sqli2)
                            except:
                                pass
                            if poi_ch_name =='':
                                r1 = 0
                            if poi_en_name == '':
                                r2 = 0
                            print 'checked results：','cn_name',r1,'english_name',r2
                            if r1 or r2:
                                print 'already here,upgrade ... ...'
                                pass
                            else:
                                print 'insert new POI... ...'
                                cur.execute(sqli,(poi_ch_name, poi_en_name, poi_loc_name, tag_id,poi_score,poi_rank,poi_address,poi_telephone,comments_count,source))
                                conn.commit()
                            print '------------------------------------------------'
    cur.close()
    conn.close()
    print '------------finished--------------'
