#!/usr/bin/env python3
'''
This software was created by United States Government employees at 
The Center for Cybersecurity and Cyber Operations (C3O) 
at the Naval Postgraduate School NPS.  Please note that within the 
United States, copyright protection is not available for any works 
created  by United States Government employees, pursuant to Title 17 
United States Code Section 105.   This software is in the public 
domain and is not subject to copyright. 
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
  1. Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.
  2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
'''
from flask import Flask, render_template, url_for, send_file, Response, request
import json
import sys
import os
import glob
from flask_table import Table, Col, LinkCol, create_table, NestedTableCol

'''
Use the Flask framework to create dynamic web pages displaying student goals
and the intermediate results and raw artifacts.
'''

class HackLinkCol(LinkCol):
    def td_format(self, content):
        if ':' in content:
            return content.rsplit(':', 1)[1]
        else:
            return content
class HackCol(Col):
    def td_format(self, content):
        if ':' in content:
            return content.rsplit(':', 1)[1]
        else:
            return content

app = Flask(__name__)
data_dir = '/home/mike/tmp'
#lab = 'telnetlab'
lab = 'capabilities'
lab_dir = os.path.join(data_dir, lab)

tbl_options = dict(no_items='Empty',   border='1px solid black')

def getGoalDoc():
    retval = ''
    fname = '%s.grades.txt' % lab
    grade_file = os.path.join(lab_dir, fname)
    with open(grade_file) as fh:
        got_it = False
        for line in fh:
            if got_it:
                line = retval + line
            if line.startswith('What is automatically'):
                got_it = True
                retval = line
    return retval

@app.route('/grades')
def grades():

    json_fname = '%s.grades.json' % lab
    grade_json = os.path.join(lab_dir, json_fname)
    rows = []
    #TableCls = create_table('TableCls')\
    #        .add_column('name', Col('Name'))
    GoalTableCls = create_table('GoalTableCls', options=tbl_options)\
            .add_column('name', LinkCol('Name', 'student_select',
                   url_kwargs=dict(student_id='full_name'), attr='name'))

    with open(grade_json) as fh:
        grade_dict = json.load(fh)
        first_key = list(grade_dict.keys())[0]
        for goal in grade_dict[first_key]['grades']:
            if not goal.startswith('_'):
                #GoalTableCls.add_column(goal, Col(goal))
                GoalTableCls.add_column(goal, HackLinkCol(goal, 'goal_select',
                   url_kwargs=dict(student_id='full_name', goal=goal, timestamp='timestamp'), attr=goal))
        for student in grade_dict:
            row = {}
            parts = student.split('_at_')
            row['name'] = parts[0]
            row['full_name'] = student
            row['timestamp'] = 'None'
            for key in grade_dict[student]['grades']:
                if not key.startswith('_'):
                    row[key] = '%s:%s' % (key, grade_dict[student]['grades'][key])
            rows.append(row)
        tbl = GoalTableCls(rows) 
            
        goal_doc = getGoalDoc()
    return render_template('grades.html', lab=lab, table=tbl, goal_doc=goal_doc)

def findTS(student_dir, student_id, container_list, ts, search_string):
    glob_mask = '*.%s' % ts
    sub_tbl = []
    student_dir = os.path.join(lab_dir, student_id)
    for container_id in container_list:
        result_dir = os.path.join(student_dir, container_id, '.local', 'result')
        ts_list = glob.glob(os.path.join(result_dir, glob_mask))
        container = container_id.split('.')[1]
        for ts_path in ts_list:
            if len(search_string) > 0:
                with open(ts_path) as fh:
                    data = fh.read()
                    if search_string not in data:
                        continue
                
            row = {}
            ts = os.path.basename(ts_path) 
            fname = ts.rsplit('.',1)[0]
            row['container'] = container
            row['container_id'] = container_id
            row['fname'] = fname
            row['ts'] = ts
            row['result_dir'] = result_dir
            row['student_id'] = student_id
            row['search_string'] = search_string
            sub_tbl.append(row)
    return sub_tbl
            
@app.route('/grades/<string:student_id>', methods=['GET', 'POST'])
def student_select(student_id):

    class RawSubTable(Table):
        container = Col('')
        fname = LinkCol('', 'raw_select',
                   url_kwargs=dict(student_id='student_id',container_id='container_id',
                      ts='ts', fname='fname'), attr='fname')

    BoolTableCls = create_table('BoolTableCls', options = tbl_options)
    BoolTableCls.add_column('name', Col('Name'))
    BoolTableCls.add_column('value', Col('Value'))

    student_dir = os.path.join(lab_dir, student_id)
    student_inter_dir = os.path.join(student_dir, '.local','result')
    bool_results_file = os.path.join(student_inter_dir, lab)
    bool_tbl = []
    with open(bool_results_file) as fh:
        br = json.load(fh)
        for b in br:
            row = {}
            if b.startswith('_') or b == 'PROGRAM_ENDTIME':
                continue
            row['name'] = b
            row['value'] = br[b]
            bool_tbl.append(row)
    tbl = BoolTableCls(bool_tbl)

    container_list = os.listdir(student_dir)
    
    TS_TableCls = create_table('TS_TableCls', options=tbl_options)\
            .add_column('ts', LinkCol('ts', 'ts_select',
                   url_kwargs=dict(ts='ts', student_id='student_id'), attr='ts'))

    TS_TableCls.add_column('raw_links', NestedTableCol('Raw artifacts', RawSubTable))
    search_string = request.form.get('search')
    if search_string is None:
        search_string = ''
    else: 
        search_string = search_string.strip()
    print('search_string is <%s>' % search_string)

    glob_mask = '%s.*' % lab 
    ts_list = glob.glob(os.path.join(student_inter_dir, glob_mask))
    ts_rows = []
    for ts in ts_list:
        base = os.path.basename(ts)
        ts_suffix = base.rsplit('.')[-1]
        raw_tbl = findTS(student_dir, student_id, container_list, ts_suffix, search_string)
        if len(raw_tbl) > 0:
            row = {}
            row['ts'] = ts_suffix
            row['raw_links'] = raw_tbl
            row['student_id'] = student_id
            ts_rows.append(row)
    ts_tbl = TS_TableCls(ts_rows)

    hist_list = []
    for full_container in container_list:
        if os.path.isfile(os.path.join(student_dir, full_container, '.bash_history')):
            container = full_container.split('.')[1]
            url = 'history/%s/%s' % (student_id, full_container)
            entry = [container, url]
            hist_list.append(entry)

    student_email = student_id.rsplit('.', 1)[0]
    return render_template('student.html', student_email=student_email, table = tbl, ts_table = ts_tbl, 
          hist_list = hist_list, search_string=search_string, back_grades=url_for('grades'))

@app.route('/grades/ts/<student_id>/<string:ts>')
def ts_select(student_id, ts):
    student_dir = os.path.join(lab_dir, student_id)
    student_inter_dir = os.path.join(student_dir, '.local','result')
    ts_file = '%s.%s' % (lab, ts)
    ts_path = os.path.join(student_inter_dir, ts_file)
    with open(ts_path) as fh:
        data = fh.read()
    
    student_email = student_id.rsplit('.', 1)[0]
    return render_template('ts.html', student_id=student_email, ts=ts, data = data, back_grades=url_for('grades'))
    

@app.route('/grades/<student_id>/<container_id>/history')
def history(student_id, container_id):
   
    container_history = os.path.join(lab_dir, student_id, container_id, '.bash_history')
    with open(container_history) as fh:
        data = fh.read()
    
    student_email = student_id.rsplit('.', 1)[0]
    return render_template('history.html', student_id=student_email, data = data, back_grades=url_for('grades'))


@app.route('/grades/raw/<student_id>/<container_id>/<ts>/<fname>')
def raw_select(student_id, container_id, ts, fname):
    result_dir = os.path.join(lab_dir, student_id, container_id, '.local', 'result')
    path = os.path.join(result_dir, ts)
    with open(path) as fh:
        data = fh.read()
    
    container = container_id.split('.')[1]
    student_email = student_id.rsplit('.', 1)[0]
    return render_template('raw.html', student_id=student_email, timestamp=ts, fname=fname, 
          container=container,data = data, back_grades=url_for('grades'))


def getGoal(goals_json, goal_id):
    for goal_entry in goals_json:
        if goal_entry['goalid'] == goal_id:
            return goal_entry
    return None

def getBoolTable(student_id, student_inter_dir, goal_id, goals_json, bool_tbl_list, did_these):
    bool_json_file = 'bool_%s.json' % goal_id
    bool_json_path = os.path.join(student_inter_dir, bool_json_file)
    with open(bool_json_path) as fh:
        bool_json = json.load(fh)
    first_key = list(bool_json.keys())[0]
    BoolExpTableCls = create_table('BoolExpTableCls', options = tbl_options)
    BoolExpTableCls.add_column('timestamp', Col('Timestamp'))

    goal_entry = getGoal(goals_json, goal_id) 
    bool_string = goal_entry['boolean_string'] 
    ''' hack to ensure whitespace before and after each item in expression '''
    the_string = bool_string.replace('(', ' ')
    the_string = the_string.replace(')', ' ')
    ''' order table based on order of items in the expression '''
    item_list = the_string.split(' ')
    for item in item_list:
        item = item.strip()
        if item in bool_json[first_key]:
            goal_entry = getGoal(goals_json, item)
            if goal_entry is None:
                BoolExpTableCls.add_column(item, HackLinkCol(item, 'result_select',
                   url_kwargs=dict(student_id='student_id', timestamp='timestamp', 
                   result=item), attr=item))
            elif goal_entry['goaltype'] == 'boolean':
                BoolExpTableCls.add_column(item, HackCol(item))
            elif goal_entry['goaltype'] == 'matchany':
                BoolExpTableCls.add_column(item, HackLinkCol(item, 'goal_select',
                   url_kwargs=dict(student_id='student_id', goal=item, timestamp='timestamp'), attr=item))
                
            else:
                ''' not handled yet '''
                BoolExpTableCls.add_column(item, HackCol(item))
                

    bool_exp_tbl_rows = []
    for ts in bool_json:
        row = {}
        row['timestamp'] = ts
        row['student_id'] = student_id
        for item in bool_json[ts]:
            if (' %s ' % item) in the_string:
                row[item] = '%s:%s' % (item, bool_json[ts][item])
        bool_exp_tbl_rows.append(row)
    bool_exp_tbl = BoolExpTableCls(bool_exp_tbl_rows)
    bool_tbl_list.append([goal_id, bool_string, bool_exp_tbl])
    ''' look for bool elements that are themselves results of boolean expressions '''
    for sub_goal_id in bool_json[first_key]:
        if sub_goal_id in did_these:
            continue
        elif (' %s ' % sub_goal_id) not in the_string:
            continue
        else:
            did_these.append(sub_goal_id)
        goal_entry = getGoal(goals_json, sub_goal_id)
        if goal_entry is not None and goal_entry['goaltype'] == 'boolean':
            bool_tbl_list = getBoolTable(student_id, student_inter_dir, sub_goal_id, goals_json, bool_tbl_list, did_these)

    return bool_tbl_list
    
@app.route('/grades/goals/<student_id>/<goal>/<timestamp>')
def goal_select(student_id, goal, timestamp):
    student_dir = os.path.join(lab_dir, student_id)
    student_inter_dir = os.path.join(student_dir, '.local','result')
    goals_json_file = os.path.join(student_inter_dir, 'goals.json')
    if '-' in timestamp:
        timestamp = timestamp.split('-')[0]
    goal_id = goal.split(':')[0]
    bool_tbl_list = []
    result_rec = None
    with open(goals_json_file) as fh:
        goals_json = json.load(fh)
        goal_entry = getGoal(goals_json, goal_id) 
        if goal_entry['goaltype'] == 'boolean':
            did_these = [goal_id]
            bool_tbl_list = getBoolTable(student_id, student_inter_dir, goal_id, goals_json, bool_tbl_list, did_these)
        elif goal_entry['goaltype'] == 'matchany':
            resulttag = goal_entry['resulttag']
            if resulttag.startswith('result.'):
                 result_id = resulttag.split('.')[1]
                 result_rec = getResultRec(student_id, timestamp, result_id)
    student_email = student_id.rsplit('.', 1)[0]
    return render_template('goal.html', lab=lab, student_email=student_email, goal = goal, 
               bool_tbl_list=bool_tbl_list, goal_entry=goal_entry, result_rec=result_rec, 
               timestamp=timestamp, back_grades=url_for('grades'))

def getResultDef(result_id):
    fname = None
    expr = None
    result_file = os.path.join(lab_dir,'.local', 'instr_config', 'results.config')
    with open(result_file) as fh:
        for line in fh:
            if line.strip().startswith('#'):
                continue
            if '=' in line:
                result, rest = line.split('=')
                if result.strip() == result_id:
                    fname, expr = rest.split(' : ', 1)
                    break
    return fname, expr

def getResultRec(student_id, timestamp, result_id):
    retval = {}
    student_dir = os.path.join(lab_dir, student_id)
    student_inter_dir = os.path.join(student_dir, '.local','result')
    goals_json_file = os.path.join(student_inter_dir, 'goals.json')
    if '-' in timestamp:
        timestamp = timestamp.split('-')[0]
    ts_file = '%s.%s' % (lab, timestamp)
    ts_results_file = os.path.join(student_inter_dir, ts_file)
    with open(ts_results_file) as fh:
        tsr = json.load(fh)
        value = tsr[result_id]
        target_file, expr = getResultDef(result_id)
        container = None
        if ':' in target_file:
            container, target_file = target_file.split(':')
        if container is None:
            glob_mask = '%s/*/' % student_dir
            dlist = glob.glob(glob_mask)
            if len(dlist) != 1:
                print('result_select expected on directory, got %s' % str(dlist))
                exit(1)
            container_id = os.path.basename(dlist[0][:-1])
            container = container_id.split('.')[1]
        else:
            container_id = '%s.%s.student' % (lab, container.strip()) 
       
        result_ts = '%s.%s' % (target_file.strip(), timestamp)
        result_path = os.path.join(student_dir, container_id, '.local', 'result', result_ts)
        with open(result_path) as fh:
            data = fh.read()
        retval['result_id'] = result_id
        retval['value'] = value
        retval['container'] = container
        retval['fname'] = target_file.strip()
        retval['expr'] = expr
        retval['data'] = data
    return retval
           
@app.route('/grades/results/ts/<student_id>/<timestamp>/<result>')
def result_select(student_id, timestamp, result):
    result_id = result.split(':')[0]
    result_rec = getResultRec(student_id, timestamp, result_id)
    student_email = student_id.rsplit('.', 1)[0]
    return render_template('result.html', student_id=student_email, result = result_rec['result_id'], 
             value=result_rec['value'], timestamp=timestamp, 
             container=result_rec['container'], expr=result_rec['expr'], 
             data=result_rec['data'], back_grades=url_for('grades'))


@app.route('/form-example', methods=['GET', 'POST']) #allow both GET and POST requests
def form_example():
    if request.method == 'POST':  #this block is only entered when the form is submitted
        language = request.form.get('language')
        framework = request.form['framework']

        return '''<h1>The language value is: {}</h1>
                  <h1>The framework value is: {}</h1>'''.format(language, framework)

    return '''<form method="POST">
                  Language: <input type="text" name="language"><br>
                  Framework: <input type="text" name="framework"><br>
                  <input type="submit" value="Submit"><br>
              </form>'''
if __name__ == '__main__':
    app.run(debug=True, port=8008, host='0.0.0.0')
       
