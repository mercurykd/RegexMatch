import sublime
import sublime_plugin
import re

ps         = None #PhantomSet
ps_panel   = None #PhantomSet

class MyExc(Exception):
    pass

class StartRegexMatchCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        r = self.view.substr(self.view.sel()[0])
        view = self.view.window().new_file()
        view.set_name('Regex Match')
        view.assign_syntax('scope:source.regex')
        if r:
            if re.match(r'(.)(.+)\1(.+)?', r):
                view.insert(edit, 0, r)
            else:
                view.insert(edit, 0, '~' + r + '~')
        else:
            view.insert(edit, 0, '~~')
            sel = view.sel()
            sel.clear()
            sel.add(sublime.Region(1, 1))
        view.set_scratch(True)

class RegexMatchCommand(sublime_plugin.TextCommand):
    name_panel = 'regex_match'
    scopes = [
        'reg_match:error_reg',
        'reg_match:green',
        'reg_match:match',
        'reg_match:groups',
        'reg_match:annotations'
    ]

    def hidePanel(self):
        if self.view.window().active_panel() == 'output.' + self.name_panel:
            self.view.window().run_command('hide_panel')

    def run(self, edit):
        global ps

        multiline = None
        rc        = None
        lines     = None

        try:
            if self.view.syntax() and self.view.syntax().scope == 'source.regex':
                ps = sublime.PhantomSet(self.view, 'regex_match')
                self.clearRegions()
                multiline, rc = self.getRegex()
                lines = self.getTestLines(multiline)
                if rc and lines:
                    r = self.getResult(rc, lines)
                    self.showResult(edit, r)
                else:
                    self.hidePanel()
            else:
                self.hidePanel()

        except MyExc as e:
            icon = None
            for k in e.args[0]:
                if k == 'icon':
                    icon = e.args[0]['icon']
            self.view.add_regions(
                e.args[0]['scope'],
                [e.args[0]['region']],
                scope='region.redish',
                annotations=[e.args[0]['annotation']],
                icon='' if icon is None else icon
            )
        except Exception as e:
            raise e

    def getResult(self, rc, lines):
        ex = []
        for region, testString in lines:
            count = 0
            lm    = []
            for m in rc.finditer(testString):
                count += 1
                gr = []
                for i, g in enumerate(m.groups(), 1):
                    gr.append({
                        'name': i,
                        'group': g,
                        'start': m.start(i),
                        'end': m.end(i),
                    })
                for g in m.groupdict():
                    gr.append({
                        'name': g,
                        'group': m.groupdict()[g],
                        'start': m.start(g),
                        'end': m.end(g),
                    })
                lm.append({
                    'count': count,
                    'start': m.start(),
                    'end': m.end(),
                    'string': testString,
                    'match': m[0],
                    'groups': gr,
                })
            if count:
                ex.append({
                    'region': region,
                    'matches': lm,
                    'explain': None,
                    'panel': {
                        'match': [],
                        'group': [],
                        'headmatch': [],
                        'headgroup': [],
                    },
                })
        return ex

    def showResult(self, edit, ex):
        global ps, ps_panel

        result = {
            'lines': [],
            'matches': [],
            'groups': [],
            'annotations' : {
                'regions' : [],
                'text' : [],
            }
        }
        for k in ex:
            result['lines'].append(k['region'])
            result['annotations']['regions'].append(sublime.Region(k['region'].b, k['region'].b))
            result['annotations']['text'].append('matched ' + str(len(k['matches'])))
            explain = 'matched ' + str(len(k['matches'])) + ':\n\n'
            for m in k['matches']:
                result['matches'].append(sublime.Region(k['region'].a + m['start'], k['region'].a + m['end']))
                explain += str(m['count']) + ':\n'

                k['panel']['match'].append(sublime.Region(len(explain) + m['start'], len(explain) + m['end']))
                for i, g in enumerate(m['groups'], 1):
                    if g['group'] is not None:
                        k['panel']['group'].append(sublime.Region(len(explain) + g['start'], len(explain) + g['end']))
                        result['groups'].append(sublime.Region(k['region'].a + g['start'], k['region'].a + g['end']))

                explain += m['string'] + '\n'
                k['panel']['headmatch'].append(sublime.Region(len(explain), len(explain) + 1))
                explain += '0:'
                if m['match']:
                    explain += m['match'] + '\n'
                else:
                    explain += 'null\n'

                for i, g in enumerate(m['groups'], 1):
                    if g['group'] is not None:
                        k['panel']['headgroup'].append(sublime.Region(len(explain), len(explain) + len(str(g['name']))))
                        explain += str(g['name']) + ':'
                        if g['group']:
                            explain += g['group'] + '\n'
                        else:
                            explain += 'null\n'

                explain += '\n'

            k['explain'] = explain

        ph = []
        for k in result:
            if result[k]:
                if k == 'lines':
                    self.view.add_regions(
                        self.scopes[1],
                        result[k],
                        scope='region.greenish',
                        icon='dot',
                        flags=sublime.HIDE_ON_MINIMAP|sublime.DRAW_NO_FILL,
                    )
                if k == 'matches':
                    m  = []

                    for i in result[k]:
                        if i.a == i.b:
                            ph.append({'color': 'f2b967', 'region': i})
                        else:
                            m.append(i)

                    if m:
                        self.view.add_regions(
                            self.scopes[2],
                            m,
                            scope='region.orangish',
                            flags=sublime.HIDE_ON_MINIMAP,
                        )

                if k == 'groups':
                    m  = []

                    for i in result[k]:
                        if i.a == i.b:
                            ph.append({'color':'5897fb', 'region': i})
                        else:
                            m.append(i)

                    if m:
                        self.view.add_regions(
                            self.scopes[3],
                            m,
                            scope='region.bluish',
                            flags=sublime.HIDE_ON_MINIMAP|sublime.DRAW_NO_FILL,
                        )
                if k == 'annotations':
                    self.view.add_regions(
                        self.scopes[4],
                        result[k]['regions'],
                        annotations=result[k]['text'],
                        annotation_color='green',
                    )
        if ph:
            self.showPhantoms(ps, ph)

        if not result['lines']:
            self.view.add_regions(
                self.scopes[0],
                [sublime.Region(self.view.size(), self.view.size())],
                annotations=['no matches'],
                annotation_color='gray'
            )

        # output panel
        p = self.view.sel()[0].a
        view_panel = self.view.window().create_output_panel(self.name_panel, True)
        ps_panel = sublime.PhantomSet(view_panel, 'regex_match')
        contain = False

        ph = []
        for k in ex:
            if k['region'].contains(p):
                if k['explain'] is not None:
                    view_panel.insert(edit, 0 , k['explain'])
                    m  = []
                    for i in k['panel']['match']:
                        if i.a == i.b:
                            ph.append({'color': 'f2b967', 'region': i})
                        else:
                            m.append(i)

                    if m:
                        view_panel.add_regions(
                            self.scopes[2],
                            m,
                            scope='region.orangish',
                        )
                    if k['panel']['group']:
                        m  = []

                        for i in k['panel']['group']:
                            if i.a == i.b:
                                ph.append({'color': '5897fb', 'region': i})
                            else:
                                m.append(i)

                        if m:
                            view_panel.add_regions(
                                self.scopes[3],
                                m,
                                scope='region.bluish',
                            )
                    if k['panel']['headmatch']:
                        view_panel.add_regions(
                            self.scopes[4],
                            k['panel']['headmatch'],
                            scope='region.orangish',
                        )
                    if k['panel']['headgroup']:
                        view_panel.add_regions(
                            self.scopes[0],
                            k['panel']['headgroup'],
                            scope='region.bluish',
                        )
                contain = True

        if ph:
            self.showPhantoms(ps_panel, ph)

        if contain:
            self.view.window().run_command('show_panel', args={'panel':'output.' + self.name_panel})
        else:
            self.hidePanel()

    def showPhantoms(self, ps, phantoms):
        ph = []
        for i in phantoms:
            ph.append(sublime.Phantom(i['region'], '<div  style="background-color:#' + i['color'] + ';margin-right:-5px;width:1px;">&nbsp;</div>', sublime.LAYOUT_INLINE))
        ps.update(ph)

    def clearRegions(self):
        for i in self.scopes:
            self.view.erase_regions(i)

    def getRegex(self):
        multiline = False
        m = re.match(r'(.)(.+)\1(.+)?', self.view.substr(self.view.full_line(0)))
        try:
            if m:
                regex = m[2]
                flags = 0
                if m[3]:
                    for i in m[3]:
                        if i == 'i':
                            flags = flags | re.I
                        elif i == 's':
                            flags = flags | re.S
                        elif i == 'u':
                            flags = flags | re.U
                        elif i == 'm':
                            flags = flags | re.M
                            multiline = True
                        else:
                            raise re.error('not supported flag "' + i + '"', pos = m[0].rfind(i) - 1)
                return [multiline, re.compile(regex, flags)]
        except re.error as e:
            raise MyExc({
                    'scope': self.scopes[0],
                    'region': sublime.Region(e.pos + 1, e.pos + 2),
                    'icon': 'circle',
                    'annotation': e.msg + ' in pos ' + str(e.pos),
                })
        except Exception as e:
            raise e
        else:
            raise MyExc({
                    'scope': self.scopes[0],
                    'region': self.view.full_line(0),
                    'annotation': 'regular expression error',
                })

    def getTestLines(self, multiline):
        region = sublime.Region(self.view.full_line(0).b, self.view.size())
        if region.a < region.b:
            if multiline:
                s = []
                for i in self.view.split_by_newlines(region):
                    s.append((i, self.view.substr(i)))
                return s
            else:
                return [(region, self.view.substr(region))]
        else:
            return []


class RegexMatchViewEventListener(sublime_plugin.ViewEventListener):
    def on_activated_async(self):
        self.view.run_command('regex_match')
    def on_selection_modified(self):
        self.view.run_command('regex_match')
