#!/usr/bin/env python
import os, re
from git import Repo
import sqlite3
from git import RemoteProgress

"""
中文翻译字数统计表
id 自增
file_path 文件路径
github_id 作者github_id
zh_version 版本号
flag 0 表示 add 1 表示 update
merge_time 日期
zh_sum 文件中包含的中文的字数
"""

db = "../db/db.sqlite"
start_time = '2019-11-03T00:00:00Z'


def get_all_data_by_pr_version(version):
    # 连接数据库
    conn = sqlite3.connect(db)
    # 创建一个 cursor
    cursor = conn.cursor()
    cursor.execute(
        "select  pr_number,pr_author,pr_merged_time,pr_version,"
        "pr_files  from docs  where process = 0  and pr_version = "
        + "'" + version + "'" + " and  pr_merged_time > '"
        + start_time + "'" + " order by pr_merged_time asc")
    data = cursor.fetchall()
    cursor.close()
    conn.commit()
    conn.close()
    return data


def get_docs_version_list():
    # 连接数据库
    conn = sqlite3.connect(db)
    # 创建一个 cursor
    cursor = conn.cursor()
    sql = "select  distinct(pr_version) from docs where pr_merged_time > '" + start_time + "'"
    cursor.execute(sql)
    all_zh_trans_version = [version[0] for version in cursor.fetchall()]
    cursor.close()
    conn.commit()
    conn.close()
    return all_zh_trans_version


class MyProgressPrinter(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        print(op_code, cur_count, max_count, cur_count / (max_count or 100.0), message or "NO MESSAGE")


def job(fetch_flag):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_path = os.path.dirname(current_dir)
    Repo.init('../istio.io')
    repo = Repo(os.path.join(parent_path, 'istio.io'))
    if len(repo.remotes) == 0:
        print("create remote origin.")
        origin = repo.create_remote('origin', "https://github.com/istio/istio.io.git")
    else:
        print("remote origin already exists.")
        origin = repo.remote('origin')
    if fetch_flag:
        for fetch_info in origin.fetch(progress=MyProgressPrinter()):
            print("......       fetch   ", fetch_info.ref, "        ......")
            print("Updated %s to %s" % (fetch_info.ref, fetch_info.commit))
    analysis_file(repo, fetch_flag)


def get_pr_number_in_commit_info(content):
    pattern = re.compile(r'#(\d+)')
    result = pattern.findall(content)[0]
    return result


def get_cn_by_diff(show_content, pr_number):
    commit_dict = {

    }
    # pr_id 确定不重复计算
    if get_pr_number_in_commit_info(show_content) == str(pr_number):
        for diff_split in show_content.split("diff --git"):
            if diff_split.find("a/content/zh/") != -1:
                file_all = diff_split.split(" ")
                file_name = file_all[1].replace("a/", "")
                file_content = "".join(file_all)
                cn_sum = cn_word_count(file_content)
                commit_dict.setdefault(file_name, cn_sum)
    return commit_dict


def get_zh_by_pr(repo, cursor, file_name, pr):
    pr_number, github_id, merged_time, version = pr[0], pr[1], pr[2], pr[3]
    git = repo.git
    try:
        content = git.log('--after=' + start_time, file_name)
    except BaseException as e:
        # 无 git log 信息的文件
        insert_into_git_problems(cursor, file_name, version, github_id, pr_number, merged_time)
    commits = list_commits(content)
    commits.reverse()
    list_data = []
    for commit in commits:
        show_content = git.show(commit)
        commit_dict = get_cn_by_diff(show_content, pr_number)
        for k, v in commit_dict.items():
            # 中文汉字数量大于 0 表示新增的翻译 为 0 表示添加的英文原文
            if v > 0:
                value = (pr_number, merged_time, version, github_id, k, v)
                list_data.append(value)
    return list_data


def insert_into_git_problems(cursor, file_name, version, github_id, pr_number, merged_time):
    sql = "select * from git_log_problems where file_path = '" + file_name + "'"
    data = cursor.execute(sql).fetchall()
    if len(data) > 0:
        print(file_name, " db existed")
    else:
        sql = " insert into  git_log_problems (file_path,zh_version," \
              "github_id,pr_number,merged_time) values (?,?,?,?,?) "
        cursor.execute(sql, (file_name, version, github_id, pr_number, merged_time))
        print(" git log_problems file_info insert into ", pr_number, github_id, merged_time, version, file_name)


def valid_file(pr):
    # 从 docs 中查询 pr_version = current_local_branch.name 的所有的数据
    pr_files = []
    for f in pr[4].split(","):
        if (os.path.splitext(f)[1] == '.md' or
                os.path.splitext(f)[1] == '.htm' or
                os.path.splitext(f)[1] == '.html'):
            pr_files.append(f)
    return pr_files


def analysis_file(repo, fetch_flag):
    # 连接数据库
    conn = sqlite3.connect(db)
    # 创建一个 cursor
    cursor = conn.cursor()

    all_zh_version = get_docs_version_list()
    current_local_branch = repo.active_branch
    for zh_trans in all_zh_version:
        # 当前节点指向的值
        if current_local_branch.name == zh_trans:
            all_data = []
            # 更新当前本地分支标志
            if fetch_flag:
                print(repo.git.pull())
            data = get_all_data_by_pr_version(zh_trans)
            for pr in data:
                pr_files = valid_file(pr)
                for file_name in pr_files:
                    list_data = get_zh_by_pr(repo, cursor, file_name, pr)
                    all_data.append(list_data)
            set_all_data = []
            for info in all_data:
                if len(info) > 0 and info not in set_all_data:
                    set_all_data.append(info)
            for insert_data in set_all_data:
                for tuple_data in insert_data:
                    github_id, pr_number, zh_version, merge_time, zh_sum, file_path \
                        = tuple_data[3], tuple_data[0], tuple_data[2], tuple_data[1], tuple_data[5], tuple_data[4]
                    cursor.execute(
                        "select pr_number,zh_version from zh_trans where zh_version = '"
                        + tuple_data[2] + "' and file_path = '" + tuple_data[4] + "'")
                    is_exist = []
                    for ii in cursor.fetchall():
                        if ii[0] not in is_exist:
                            is_exist.append(ii[0])
                    # 某版本不存在某文件的记录 则是新增
                    if len(is_exist) == 0:
                        flag = 0  # 新增翻译
                    else:
                        flag = 1
                    if pr_number in is_exist:
                        print("db existed", github_id, pr_number, zh_version, merge_time, zh_sum, flag, file_path)
                    else:
                        print("insert db", github_id, pr_number, zh_version, merge_time, zh_sum, flag, file_path)
                        insert_sql = "insert into zh_trans (github_id,pr_number,zh_version," \
                                     "merge_time,zh_sum,flag,file_path)" \
                                     "values (?,?,?,?,?,?,?)"
                        cursor.execute(insert_sql,
                                       (github_id, pr_number, zh_version, merge_time, zh_sum, flag, file_path))
                        cursor.execute(
                            "update docs set process = 1 where pr_number = '" +
                            str(pr_number) + "' and pr_version = '" + zh_version + "'")
    cursor.close()
    conn.commit()
    conn.close()


def cn_word_count(content):
    """
    功能: 单文件-中文翻译字数统计
    """
    count = 0
    result = re.findall(u"[\u4e00-\u9fa5]", content)
    for cn in result:
        count += len(cn)
    return count


def list_commits(content):
    commits = []
    for line in content.split("\n"):
        if line.find("commit") != -1:
            commits.append(line.split(" ")[-1])
    return commits


if __name__ == '__main__':
    job(fetch_flag=True)
