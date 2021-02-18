import json
import re
import smtplib
import time
import traceback
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formatdate

from file import File
from jsonRpc import JsonRpc


def sendMail(subject, content, emailTo):
    host = conf['smtp']['host']
    port = conf['smtp']['port']
    ssl = conf['smtp']['ssl']
    username = conf['smtp']['username']
    password = conf['smtp']['password']
    _from = conf['smtp']['from']

    mail = MIMEText(content.encode('utf-8'), 'plain', 'utf-8')
    mail['Subject'] = Header(subject, 'utf-8')
    mail['From'] = _from
    mail['To'] = emailTo
    mail['Date'] = formatdate()

    smtp = smtplib.SMTP_SSL(host, port) if ssl else smtplib.SMTP(host, port)
    smtp.login(username, password)
    smtp.sendmail(_from, emailTo, mail.as_string())
    smtp.close()


if __name__ == '__main__':
    conf = json.loads(File('config.json').content)

    rpc = JsonRpc(conf['jsonrpc']['url'], conf['jsonrpc']['username'], conf['jsonrpc']['password'])

    try:
        while(True):

            projects = [proj for proj in rpc.call('getAllProjects') if proj['is_active'] == '1']

            tasks = []

            for proj in projects:
                r = rpc.call('getAllTasks', project_id=int(proj['id']), status_id=1)
                tasks += [t for t in r]

            for task in tasks:
                taskId = int(task['id'])
                assigneeId = int(task['owner_id'])
                taskDueDate = int(task['date_due'])

                print(task['title'])

                diff = int(taskDueDate) - int(time.time())
                remains_day = int(diff / 86400)
                remains_hour = int(diff % 86400 / 3600)
                remains_minute = int(diff % 86400 % 3600 / 60)
                remains_single_day = int(diff / 86400)
                remains_single_hour = int(diff / 3600)
                remains_single_minute = int(diff / 60)

                print(f'day: {remains_day}, hour: {remains_hour}, min: {remains_minute}', end='  |  ')
                print(f'day: {remains_single_day}, hour: {remains_single_hour}, min: {remains_single_minute}')

                metadata = rpc.call('getTaskMetadata', task_id=int(task['id']))

                if 'notifications' not in metadata:
                    tp = {k: False for k in conf['times']}
                    rpc.call('saveTaskMetadata', task_id=taskId, values={
                        'notifications': json.dumps(tp)
                    })

                    content = 'notification registered: ' + (', '.join(tp.keys()))
                    rpc.call('createComment', task_id=taskId, user_id=3, content=content)

                ntf = json.loads(metadata['notifications'])
                updated = False
                remains_time = ''

                for remains, notified in ntf.items():
                    if re.match(r'^\d+[dhm]$', remains):
                        number = int(remains[:-1])
                        unit = remains[-1:]

                        if not notified:
                            if unit == 'd' and number > remains_single_day > 0:
                                print(f'notify for {number}{unit}')
                                ntf[remains] = True
                                updated = True
                                remains_time = f'{number}天'
                            elif unit == 'h' and number > remains_single_hour > 0:
                                print(f'notify for {number}{unit}')
                                ntf[remains] = True
                                updated = True
                                remains_time = f'{number}小时'
                            elif unit == 'm' and number > remains_single_minute >= 0:
                                print(f'notify for {number}{unit}')
                                ntf[remains] = True
                                updated = True
                                remains_time = f'{number}分钟'

                if updated:
                    rpc.call('saveTaskMetadata', task_id=int(task['id']), values={
                        'notifications': json.dumps(ntf)
                    })

                    emailTo = ''
                    if assigneeId != 0:
                        user = rpc.call('getUser', user_id=assigneeId)
                        if user['email'] != '':
                            emailTo = user['email']
                        else:
                            admin = rpc.call('getUser', user_id=conf['administrator_id'])
                            emailTo = admin['email']
                    else:
                        admin = rpc.call('getUser', user_id=conf['administrator_id'])
                        emailTo = admin['email']

                    taskTitle = task['title']
                    taskUrl = task['url']
                    taskDesc = task['description']
                    taskOverdue = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(taskDueDate))

                    subject = f'任务还有{remains_time}到期'
                    content = f'任务：{taskTitle}\n描述：{taskDesc}\n\n\n到期时间：{taskOverdue}\n跳转链接：{taskUrl}'

                    sendMail(subject, content, emailTo)
                    print('Mail sent')

                    metadata = rpc.call('getTaskMetadata', task_id=int(task['id']))

                print(metadata)

                print('')

            print('--------------')
            time.sleep(conf['check_interval'])
    except SystemExit:
        pass
    except KeyboardInterrupt:
        pass
    except BaseException:
        subject = 'TaskNotification程序异常退出'
        content = traceback.format_exc()
        receiver = conf['emergency_email']

        traceback.print_exc()
        sendMail(subject, content, receiver)
        print('Exception Reported to '+receiver)

