# -*- coding: UTF-8 -*-

import time
import datetime
import yaml
import os
import sqlite3
import requests
import re
from jinja2 import Template
from pyecharts import options as opts
from pyecharts.charts import Pie

WORKSPACE = "D:\\PythonProject\\ZH-trans\\v2\\"
CONFIG_FILE = os.path.join(WORKSPACE, 'config', 'config.yaml')


class Configuration(object):
    def __init__(self, configfile):
        with open(configfile, "r") as f:
            self.configure = yaml.safe_load(f)

    def get_config(self):
        return self.configure


class TransAnalysis(object):
    def __init__(self):
        self.config = Configuration(CONFIG_FILE).get_config()
        self.db = os.path.join(WORKSPACE, 'data', 'db.sqlite')
        self.github_token = self.config['github_token']
        self.start_time = self.config["duration"]["start"]
        self.end_time = self.config["duration"]["end"]
        if self.start_time == "":
            self.start_time = datetime.datetime.utcfromtimestamp(time.time()).strftime("%Y-%m-%dT%H:%M:%SZ")
        if self.end_time == "":
            self.end_time = datetime.datetime.utcfromtimestamp(time.time()).strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_cursor(self):
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        return conn, cursor

    '''
    提交 pr 前 10
    '''

    def get_top_10(self, flag=True):
        conn, cursor = self.get_cursor()
        select_top_10 = "select github_id,count(github_id) as total from pull_request " + \
                        " where merged_time  between '" + self.start_time + "' and  '" + self.end_time + "' " + \
                        " and base_branch = '" + self.config["repository"]["branch"] + "' " + \
                        " and number not in (" + self.config["except"] + ") " + \
                        " group by github_id order by total desc,github_id asc "
        select_top_10 += " limit " + str(self.config["chart"]["pr_top"])
        cursor.execute(select_top_10)
        data = cursor.fetchall()
        cursor.close()
        conn.commit()
        conn.close()
        return data

    '''
    每天合并的 pr 
    '''

    def get_all_each_day_pr(self):
        conn, cursor = self.get_cursor()
        select_each_day = " select strftime('%Y-%m-%d',merged_time) " \
                          " as merged_date,count(*) as total from pull_request  " + \
                          " where merged_time  between '" + self.start_time + "' and  '" + self.end_time + "' " + \
                          " and base_branch = '" + self.config["repository"]["branch"] + "' " + \
                          " and number not in (" + self.config["except"] + ") " + \
                          " group by merged_date  "
        cursor.execute(select_each_day)
        data = cursor.fetchall()
        cursor.close()
        conn.commit()
        conn.close()
        return data

    '''
    翻译中文统计
    '''

    def get_sum_zh(self, flag=False):
        conn, cursor = self.get_cursor()
        select_sum_zh = " select github_id,sum(zh_word_count) as total from pull_request " + \
                        " where merged_time between '" + self.start_time + "' and  '" + self.end_time + "' " + \
                        " and base_branch = '" + self.config["repository"]["branch"] + "' " + \
                        " and number not in (" + self.config["except"] + ") " + \
                        " group by github_id order by total desc,github_id asc "
        if flag:
            select_sum_zh += " limit " + str(self.config["chart"]["zh_sum_show"])
        else:
            select_sum_zh = " select sum(zh_word_count) as total from pull_request " + \
                            " where merged_time between '" + self.start_time + "' and  '" + self.end_time + "' " + \
                            " and base_branch = '" + self.config["repository"]["branch"] + "' " + \
                            " and number not in (" + self.config["except"] + ") "
        cursor.execute(select_sum_zh)
        data = cursor.fetchall()
        cursor.close()
        conn.commit()
        conn.close()
        return data

    '''
    前端展示的翻译统计
    '''

    def get_zh_show(self):
        data = self.get_sum_zh(flag=True)
        all_data = []
        showed_total = 0
        for zh in data:
            all_data.append((zh[0], zh[1]))
            showed_total += zh[1]
        total_data = self.get_sum_zh(flag=False)
        if len(total_data) > 0:
            all_data.append(("other", total_data[0][0] - showed_total))
        print(all_data)
        return all_data

    '''
    participants 前 10 名
    '''

    def get_participant_name(self):
        conn, cursor = self.get_cursor()
        select_participant = " select participant_login from pull_request " + \
                             " where merged_time between '" + self.start_time + "' and  '" + self.end_time + "' " + \
                             " and base_branch = '" + self.config["repository"]["branch"] + "' " + \
                             " and number not in (" + self.config["except"] + ") "
        cursor.execute(select_participant)
        data = cursor.fetchall()
        reviews_count = {}
        for i in data:
            for name in i[0].split(","):
                if reviews_count.get(name) is None:
                    reviews_count.__setitem__(name, 1)
                else:
                    reviews_count.__setitem__(name, reviews_count.__getitem__(name) + 1)
        participant_sort = sorted(reviews_count.items(), key=lambda x: x[1], reverse=True)
        data = participant_sort[:self.config["chart"]["pr_participants_top"]]
        cursor.close()
        conn.commit()
        conn.close()
        return data

    '''
    reviewers 前 10 名
    '''
    def get_reviewers_top_10(self):
        conn, cursor = self.get_cursor()
        select_reviewer = " select review_login from pull_request " + \
                          " where merged_time between '" + self.start_time + "' and  '" + self.end_time + "' " + \
                          " and base_branch = '" + self.config["repository"]["branch"] + "' " + \
                          " and number not in (" + self.config["except"] + ") "
        cursor.execute(select_reviewer)
        data = cursor.fetchall()
        reviews_count = {}
        for i in data:
            for name in i[0].split(","):
                if reviews_count.get(name) is None:
                    reviews_count.__setitem__(name, 1)
                else:
                    reviews_count.__setitem__(name, reviews_count.__getitem__(name) + 1)
        participant_sort = sorted(reviews_count.items(), key=lambda x: x[1], reverse=True)
        data = participant_sort[:self.config["chart"]["pr_reviewers_top"]]
        cursor.close()
        conn.commit()
        conn.close()
        return data

    '''
    participants 每天参与 pr 的人数统计
    '''
    def get_participants_each_day(self):
        conn, cursor = self.get_cursor()
        select_participant = " select strftime('%Y-%m-%d',merged_time) as merged_date, " \
                             " participant_login as participant  from pull_request " + \
                             " where merged_time between '" + self.start_time + "' and  '" + self.end_time + "' " + \
                             " and base_branch = '" + self.config["repository"]["branch"] + "' " + \
                             " and number not in (" + self.config["except"] + ") "
        cursor.execute(select_participant)
        data = cursor.fetchall()
        date_participants = {}
        for d in data:
            for name in d[0].split(","):
                if date_participants.get(name) is None:
                    date_participants.__setitem__(name, len(d[1].split(",")))
                else:
                    date_participants.__setitem__(name, date_participants.__getitem__(name) + len(d[1].split(",")))
        cursor.close()
        conn.commit()
        conn.close()
        return date_participants

    def ensure_tables(self):
        conn, cursor = self.get_cursor()
        cursor.execute(
            "SELECT * FROM sqlite_master WHERE type='table' AND name='pull_request'"
        )
        if cursor.fetchone() is None:
            cursor.execute('''
                            create table pull_request (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                number int(20),
                                github_id varchar(255),
                                merged_by varchar(255),
                                create_time varchar(255),
                                merged_time varchar(255),
                                assignee_login varchar(1000),
                                review_login varchar(1000),
                                participant_login varchar(1000),
                                base_branch varchar(100),
                                zh_word_count int(20)
                            )''')
            print("create table pull_request successful")
        cursor.close()
        conn.commit()
        conn.close()

    def query_github_v4(self, query):
        r = requests.post("https://api.github.com/graphql",
                          json={"query": query},
                          headers={
                              "Authorization": "token %s" % self.github_token,
                              "Accept": "application/vnd.github.ocelot-preview+json",
                              "Accept-Encoding": "gzip"
                          })
        r.raise_for_status()
        reply = r.json()
        return reply

    def query_github_pr_diff(self, number):
        # https://patch-diff.githubusercontent.com/raw/kubernetes/kubernetes/pull/number.diff 最终跳转到该 url
        # 如 https://patch-diff.githubusercontent.com/raw/kubernetes/kubernetes/pull/85893.diff
        pr_diff_url = "https://github.com/" + self.config['repository']['owner'] + "/" + self.config['repository'][
            'name'] + "/pull/" + str(number) + ".diff"
        r = requests.get(pr_diff_url)
        r.raise_for_status()
        return r.text

    def calc_zh_word_count(self, content):
        count = 0
        result = re.findall(u"[\u4e00-\u9fa5]", content)
        for cn in result:
            count += len(cn)
        return count

    def analysis_prs(self, next_cursor=""):
        batch_prs = []
        if next_cursor == "":
            query = Template("""
                query {
                    repository(name: "{{ name }}", owner: "{{ owner }}") {
                        pullRequests(
                            first: 100,
                            states: MERGED,
                            labels: "{{ trans_label }}") {
                            pageInfo {
                                endCursor
                                hasPreviousPage
                                hasNextPage
                            }
                            edges {
                                node {
                                    number
                                    createdAt
                                    mergedAt
                                    mergedBy {
                                        login
                                    }
                                    assignees(first: 30) {
                                        nodes {
                                          name
                                        }
                                    }
                                    author {
                                        login
                                    }
                                    baseRef {
                                        name
                                    }
                                    reviews(first:30, states:APPROVED){
                                        nodes{
                                          author{
                                            login
                                          }
                                        }
                                    }
                                    participants(first:30){
                                        nodes{
                                          login
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                """).render({
                "name": self.config["repository"]["name"],
                "owner": self.config["repository"]["owner"],
                "trans_label": self.config["repository"]["trans_label"]
            })
            result = self.query_github_v4(query)
            has_next_page = result["data"]["repository"]["pullRequests"]["pageInfo"]["hasNextPage"]
            next_cursor = result["data"]["repository"]["pullRequests"]["pageInfo"]["endCursor"]
            prs = result["data"]["repository"]["pullRequests"]["edges"]
            for pr in prs:
                pr_number = pr["node"]["number"]
                pr_github_id = pr["node"]["author"]["login"]
                pr_merged_time = pr["node"]["mergedAt"]
                pr_base_branch = pr["node"]["baseRef"]["name"]

                pr_create_at_time = pr["node"]["createdAt"]
                pr_merged_by = pr["node"]["mergedBy"]["login"]

                reviews_logins = [n for n in [author for author in pr["node"]["reviews"]["nodes"]]]
                reviews_login = [login['login'] for login in [i["author"] for i in [n for n in reviews_logins]]]
                if len(reviews_login) > 0:
                    reviews_login = ','.join(reviews_login)
                else:
                    reviews_login = None

                assignees_logins = [n["name"] for n in [i for i in pr["node"]["assignees"]["nodes"]]]
                if len(assignees_logins) > 0:
                    assignees_login = ','.join(assignees_logins)
                else:
                    assignees_login = None

                participants_logins = []
                for name in pr["node"]["participants"]["nodes"]:
                    if name['login'] == 'googlebot' or name['login'] == 'istio-testing':
                        pass
                    else:
                        participants_logins.append(name['login'])

                if len(participants_logins) > 0:
                    participants_login = ','.join(participants_logins)
                else:
                    participants_login = None

                print([pr_number, pr_github_id, pr_merged_by, pr_create_at_time, pr_merged_time, assignees_login,
                       reviews_login, participants_login, pr_base_branch])
                batch_prs.append(
                    [pr_number, pr_github_id, pr_merged_by, pr_create_at_time, pr_merged_time, assignees_login,
                     reviews_login, participants_login, pr_base_branch])
            self.insert_merged_prs(batch_prs)
            if has_next_page:
                self.analysis_prs(next_cursor)
        else:
            query = Template("""
                query {
                    repository(name: "{{ name }}", owner: "{{ owner }}") {
                        pullRequests(
                            first: 100,
                            states: MERGED,
                            labels: "{{ trans_label }}",
                            after: "{{ next_cursor }}" ) {
                            pageInfo {
                                endCursor
                                hasPreviousPage
                                hasNextPage
                            }
                            edges {
                                node {
                                    number
                                    createdAt
                                    mergedAt
                                    mergedBy {
                                        login
                                    }
                                    assignees(first: 30) {
                                        nodes {
                                          name
                                        }
                                    }
                                    author {
                                        login
                                    }
                                    baseRef {
                                        name
                                    }
                                    reviews(first:30, states:APPROVED){
                                        nodes{
                                          author{
                                            login
                                          }
                                        }
                                    }
                                    participants(first:30){
                                        nodes{
                                          login
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                """).render({
                "name": self.config["repository"]["name"],
                "owner": self.config["repository"]["owner"],
                "trans_label": self.config["repository"]["trans_label"],
                "next_cursor": next_cursor
            })
            result = self.query_github_v4(query)
            has_next_page = result["data"]["repository"]["pullRequests"]["pageInfo"]["hasNextPage"]
            next_cursor = result["data"]["repository"]["pullRequests"]["pageInfo"]["endCursor"]
            prs = result["data"]["repository"]["pullRequests"]["edges"]
            for pr in prs:
                pr_number = pr["node"]["number"]
                pr_github_id = pr["node"]["author"]["login"]
                pr_merged_time = pr["node"]["mergedAt"]
                pr_base_branch = pr["node"]["baseRef"]["name"]

                pr_create_at_time = pr["node"]["createdAt"]
                pr_merged_by = pr["node"]["mergedBy"]["login"]

                reviews_logins = [n for n in [author for author in pr["node"]["reviews"]["nodes"]]]
                reviews_login = [login['login'] for login in [i["author"] for i in [n for n in reviews_logins]]]
                if len(reviews_login) > 0 and reviews_login[0] is not None:
                    reviews_login = ','.join(reviews_login)
                else:
                    reviews_login = None

                assignees = pr["node"]["assignees"]["nodes"]
                assignees_logins = [n["name"] for n in [i for i in assignees]]

                if len(assignees_logins) > 0 and assignees_logins[0] is not None:
                    assignees_login = ','.join(assignees_logins)
                else:
                    assignees_login = None

                participants_logins = []
                for name in pr["node"]["participants"]["nodes"]:
                    if name['login'] == 'googlebot' or name['login'] == 'istio-testing' or \
                            name['login'] == 'istio-policy-bot':
                        pass
                    else:
                        participants_logins.append(name['login'])

                if len(participants_logins) > 0 and participants_logins[0] is not None:
                    participants_login = ','.join(participants_logins)
                else:
                    participants_login = None

                print([pr_number, pr_github_id, pr_merged_by, pr_create_at_time, pr_merged_time, assignees_login,
                       reviews_login, participants_login, pr_base_branch])
                batch_prs.append(
                    [pr_number, pr_github_id, pr_merged_by, pr_create_at_time, pr_merged_time, assignees_login,
                     reviews_login, participants_login, pr_base_branch])
            self.insert_merged_prs(batch_prs)
            if has_next_page:
                self.analysis_prs(next_cursor)

    def insert_merged_prs(self, prs):
        conn, cursor = self.get_cursor()
        insert_sql = "insert into pull_request (number,github_id,merged_time," \
                     "merged_by,create_time,merged_time,assignee_login,review_login," \
                     "participant_login,base_branch,zh_word_count) values (?, ?, ?, ?, ?, ?, ?, ?, ? ,?,?)"
        for pr in prs:
            number, github_id, merged_by, create_time, merged_time, assignee_login, \
            review_login, participant_login, base_branch = \
                pr[0], pr[1], pr[2], pr[3], pr[4], pr[5], pr[6], pr[7], pr[
                    8]
            cursor.execute("select * from pull_request where number = '" + str(number) + "'")
            if cursor.fetchone() is None:
                zh_word_count = self.calc_zh_word_count(self.query_github_pr_diff(number))
                print("analysis: pr_number ", number, "; zh_word_count ", zh_word_count)
                cursor.execute(insert_sql, (
                    number, github_id, merged_by ,merged_time, create_time, merged_time, assignee_login, review_login,
                    participant_login, base_branch, zh_word_count))
                conn.commit()
        cursor.close()
        conn.commit()
        conn.close()


class ChartGenerator(object):
    def __init__(self, flag=1):
        self.config = Configuration(CONFIG_FILE).get_config()
        self.db = os.path.join(WORKSPACE, 'data', 'db.sqlite')
        self.start_time = self.config["duration"]["start"]
        self.end_time = self.config["duration"]["end"]
        if self.start_time == "":
            self.start_time = datetime.datetime.utcfromtimestamp(time.time()).strftime("%Y-%m-%dT%H:%M:%SZ")
        if self.end_time == "":
            self.end_time = datetime.datetime.utcfromtimestamp(time.time()).strftime("%Y-%m-%dT%H:%M:%SZ")

    def gen_chart(self):
        select_sql = "select github_id,sum(zh_word_count) as total from pull_request " + \
                     "where merged_time between '" + self.start_time + "' and  '" + self.end_time + "' " + \
                     "and base_branch = '" + self.config["repository"]["branch"] + "' " + \
                     "and number not in (" + self.config["except"] + ") " + \
                     "group by github_id order by total desc limit 25"
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute(select_sql)
        data = cursor.fetchall()
        all_data = []
        showed_total = 0
        for zh in data:
            all_data.append([zh[0], zh[1]])
            showed_total += zh[1]

        select_sql = "select sum(zh_word_count) as total from pull_request " + \
                     "where merged_time between '" + self.start_time + "' and  '" + self.end_time + "' " + \
                     "and base_branch = '" + self.config["repository"]["branch"] + "' " + \
                     "and number not in (" + self.config["except"] + ") "
        cursor.execute(select_sql)
        data = cursor.fetchone()
        total = data[0]
        other_count = total - showed_total
        all_data.append(["other", other_count])

        now_time = str(time.strftime('%Y-%m-%d', time.localtime(time.time()))).replace("-", "")

        # Pie chart
        pie = Pie(init_opts=opts.InitOpts(width="1200px", page_title=self.config["chart"]["title"]))
        pie.add(self.config["chart"]["series"], data_pair=all_data, center=["50%", "50%"]).set_global_opts(
            title_opts=opts.TitleOpts(title=self.config["chart"]["title"]),
            legend_opts=opts.LegendOpts(pos_top="10%", pos_left="80%", orient='vertical')
        )
        pie.render(WORKSPACE + "/output/" + now_time + "_page_pie.html")

        cursor.close()
        conn.commit()
        conn.close()


if __name__ == '__main__':
    trans_analysis = TransAnalysis()
    # trans_analysis.ensure_tables()
    # trans_analysis.analysis_prs()
    trans_analysis.get_participants_each_day()

    # chart_gen = ChartGenerator()
    # chart_gen.gen_chart()
    print("All work done ^_^")
