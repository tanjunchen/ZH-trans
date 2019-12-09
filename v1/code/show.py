#!/usr/bin/env python

import time, datetime, yaml, os, sqlite3
from pyecharts import options as opts
from pyecharts.charts import Pie, Bar


class Show(object):

    def __init__(self, begin_time=None, end_time=None, flag=1):
        with open('config.yaml', 'r', encoding="utf-8") as file:
            config = yaml.safe_load(file.read())
        self.db_path = config['istio']['db']['path']
        if not os.path.exists(self.db_path):
            os.mkdir(self.db_path)
        self.db = self.db_path + config['istio']['db']['db']
        self.start_time = config['istio']['init']['start_time']
        self.branch = config['istio']['branch']
        if begin_time is None or begin_time < self.start_time:
            self.begin_time = self.start_time
        else:
            self.end_time = end_time
        if end_time is None:
            now_stamp = time.time()
            end_time = datetime.datetime.utcfromtimestamp(now_stamp).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.end_time = end_time
        else:
            self.end_time = end_time
        self.flag = flag

    def get_github_id_sum(self):
        select_sql = "select github_id,sum(zh_sum) as total from zh_trans  where flag = " \
                     + str(self.flag) + " and  merge_time between '" + self.begin_time + "' and  '" + \
                     self.end_time + "'  group by  github_id   order by total desc"
        # 连接数据库
        conn = sqlite3.connect(self.db)
        # 创建一个 cursor
        cursor = conn.cursor()
        cursor.execute(select_sql)
        data = cursor.fetchall()
        all_data = []
        all_author = []
        all_value = []
        total = 0
        for zh in data:
            all_author.append(zh[0])
            all_value.append((zh[1]))
            all_data.append([zh[0], zh[1]])
            total += zh[1]
        if self.flag == 0:
            series_name = "开始时间：" + self.begin_time + "  结束时间：" + self.end_time + "\n istio.io 新增中文翻译字数统计 总参与人数为：" + str(
                len(all_data)) + "\n istio.io 新增中文翻译字数统计 总翻译字数为：" + str(total)
        else:
            series_name = "开始时间：" + self.begin_time + "  结束时间：" + self.end_time + "\n istio.io 更新中文翻译字数统计 总参与人数为：" + str(
                len(all_data)) + "\n istio.io 更新中文翻译字数统计 总翻译字数为：" + str(total)

        generated_log(series_name, self.flag)
        # 饼图
        pie = Pie()
        pie.add("", data_pair=all_data, center=["40%", "62%"], radius=["0%", "45%"], rosetype='radius').set_global_opts(
            title_opts=opts.TitleOpts(title=""),
            legend_opts=opts.LegendOpts(orient="vertical", pos_top="5%", pos_right="6%")).set_series_opts(
            label_opts=opts.LabelOpts(horizontal_align=True, formatter="{b}: {c}"))
        html_time = str(time.strftime('%Y-%m-%d', time.localtime(time.time()))).replace("-", "")
        if self.flag == 0:
            pie.render(html_time + "page_pie_add.html")
        else:
            pie.render(html_time + "page_pie_update.html")

        # 柱状图
        bar = (
            Bar().add_xaxis(all_author).add_yaxis("github账户", all_value).set_global_opts(
                title_opts=opts.TitleOpts(title="翻译统计"))
        )
        if self.flag == 0:
            bar.render(html_time + "page_bar_add.html")
        else:
            bar.render(html_time + "page_bar_update.html")

        cursor.close()
        conn.commit()
        conn.close()


def generated_log(content, flag):
    path = "../log"
    if not os.path.exists(path):
        os.mkdir(path)
    else:
        content = "\n\n" + content
    if flag == 1:
        with open("../log/log_update.md", encoding="utf-8", mode="a+")as f:
            f.write(content)
    elif flag == 0:
        with open("../log/log_add.md", encoding="utf-8", mode="a+")as f:
            f.write(content)


if __name__ == '__main__':
    show = Show(flag=0)
    show.get_github_id_sum()

    show2 = Show(flag=1)
    show2.get_github_id_sum()
