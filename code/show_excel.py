#!/usr/bin/env python
import time, datetime, sqlite3
import pandas as pd


def job():
    begin_time = "2019-11-03T00:00:00Z"
    now_stamp = time.time()
    flag = 0
    end_time = datetime.datetime.utcfromtimestamp(now_stamp).strftime("%Y-%m-%dT%H:%M:%SZ")
    select_update_sql = "select github_id,sum(zh_sum) as total from zh_trans  where flag = " \
                        + str(flag) + " and  merge_time between '" + begin_time + "' and  '" + \
                        end_time + "'  group by  github_id   order by total desc"
    # 连接数据库
    conn = sqlite3.connect("../data/db.sqlite")
    data_add_df = pd.read_sql(select_update_sql, conn)
    data_add_df = data_add_df.sort_values(by="github_id", ascending=True)
    docs_dff = pd.read_sql(
        " select pr_author as github_id,count(pr_number) as pr_sum from  docs  where pr_merged_time > "
        " '2019-11-03T00:00:00Z'  and pr_version='master' group by pr_author ", conn)
    docs_dff = docs_dff.sort_values(by="github_id", ascending=True)
    add_data_df = pd.merge(data_add_df, docs_dff).sort_values(by=["total", "pr_sum"], ascending=False)
    add_data_df.rename(columns={"github_id": "github账号", "total": "翻译中文字总数", "pr_sum": "pr的总数"}, inplace=True)

    flag = 1
    select_update_sql = "select github_id,sum(zh_sum) as total from zh_trans  where flag = " \
                        + str(flag) + " and  merge_time between '" + begin_time + "' and  '" + \
                        end_time + "'  group by  github_id   order by total desc"
    # 连接数据库
    data_update_df = pd.read_sql(select_update_sql, conn)
    data_update_df = data_update_df.sort_values(by="github_id", ascending=True)
    update_data_df = pd.merge(data_update_df, docs_dff).sort_values(by=["total", "pr_sum"], ascending=False)
    update_data_df.rename(columns={"github_id": "github账号", "total": "翻译中文字总数", "pr_sum": "pr的总数"}, inplace=True)

    print("begin_time", begin_time, "end_time", end_time)
    begin_time = begin_time[:begin_time.index("T")]
    end_time = end_time[:end_time.index("T")]

    writer = pd.ExcelWriter("../data/" + "istio 中文翻译统计表.xlsx", encoding="utf-8")
    add_data_df.to_excel(writer, sheet_name='新增翻译', index=False)
    update_data_df.to_excel(writer, sheet_name='更新翻译', index=False)
    writer.save()
    conn.commit()
    conn.close()


if __name__ == '__main__':
    job()
