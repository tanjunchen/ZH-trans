#!/usr/bin/env python

import sqlite3
import time, datetime
from pyecharts import options as opts
from pyecharts.charts import Pie

db = "../db/db.sqlite"
start_time = '2019-11-03T00:00:00Z'


def get_github_id_sum(start, end, flag):
    if start <= start_time:
        start = start_time
    select_sql = "select github_id,sum(zh_sum) as total from zh_trans  where flag = " \
                 + str(flag) + " and  merge_time between '" + start + "' and  '" + \
                 end + "'  group by  github_id   order by total desc"
    # 连接数据库
    conn = sqlite3.connect(db)
    # 创建一个 cursor
    cursor = conn.cursor()
    cursor.execute(select_sql)
    data = cursor.fetchall()
    all_data = []
    total = 0
    for zh in data:
        all_data.append([zh[0], zh[1]])
        total += zh[1]
    if flag == 0:
        series_name = "开始时间：" + start + "  结束时间：" + end + "\n istio.io 新增中文翻译字数统计 总参与人数为：" + str(
            len(all_data)) + "\n istio.io 新增中文翻译字数统计 总翻译字数为：" + str(total)
    else:
        series_name = "开始时间：" + start + "  结束时间：" + end + "\n istio.io 更新中文翻译字数统计 总参与人数为：" + str(
            len(all_data)) + "\n istio.io 更新中文翻译字数统计 总翻译字数为：" + str(total)

    pie = Pie()
    pie.add("", data_pair=all_data, center=["40%", "62%"], radius=["0%", "45%"], rosetype='radius').set_global_opts(
        title_opts=opts.TitleOpts(title=series_name),
        legend_opts=opts.LegendOpts(orient="vertical", pos_top="5%", pos_right="6%")).set_series_opts(
        label_opts=opts.LabelOpts(horizontal_align=True, formatter="{b}: {c}"))
    pie.render("rose.html")
    cursor.close()
    conn.commit()
    conn.close()


if __name__ == '__main__':
    now_stamp = time.time()
    utc_time = datetime.datetime.utcfromtimestamp(now_stamp).strftime("%Y-%m-%dT%H:%M:%SZ")
    get_github_id_sum(start_time, utc_time, 0)
