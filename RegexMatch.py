import sublime
import sublime_plugin
import re

ps = None #PhantomSet
# scopes
scopes = [
    'reg_match:error_reg',
    'reg_match:green',
    'reg_match:match',
    'reg_match:groups',
    'reg_match:annotations'
 ]

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
    def run(self, edit):
        global ps, scopes

        multiline = None
        rc        = None
        lines     = None

        ps = sublime.PhantomSet(self.view, 'regex_match')

        # clean regions
        self.clearRegions()

        try:
            if self.view.syntax() and self.view.syntax().scope == 'source.regex':
                multiline, rc = self.getRegex()
                lines = self.getTestLines(multiline)

                if rc and lines:
                    result = self.getResult(rc, lines)
                    self.showResult(result)

        except MyExc as e:
            self.view.add_regions(
                e.args[0]['scope'],
                [e.args[0]['region']],
                scope='region.redish',
                annotations=[e.args[0]['annotation']],
                icon=None if e.args[0]['icon'] is None else e.args[0]['icon']
            )
        except Exception as e:
            raise e

    def getResult(self, rc, lines):
        result = {
            'lines': [],
            'matches': [],
            'groups': [],
            'annotations' : {
                'regions' : [],
                'text' : [],
            }
        }
        for region, testString in lines:
            count = 0
            for m in rc.finditer(testString):
                count += 1
                result['matches'].append(sublime.Region(region.a + m.start(), region.a + m.end()))
                for g in m.groups():
                    result['groups'].append(sublime.Region(region.a + m.start() + m[0].find(g), region.a + m.start() + m[0].find(g) + len(g)))
                gd = m.groupdict()
                for g in gd:
                    result['groups'].append(sublime.Region(region.a + m.start() + m[0].find(gd[g]), region.a + m.start() + m[0].find(gd[g]) + len(gd[g])))
            if count:
                result['lines'].append(region)
                result['annotations']['regions'].append(region)
                result['annotations']['text'].append('matched ' + str(count))
        return result

    def showResult(self, result):
        global scopes

        for k in result:
            if result[k]:
                if k == 'lines':
                    self.view.add_regions(
                        scopes[1],
                        result[k],
                        scope='region.greenish',
                        icon='dot',
                        flags=sublime.HIDE_ON_MINIMAP|sublime.DRAW_NO_FILL,
                    )
                if k == 'matches':
                    m  = []
                    ph = []

                    for i in result[k]:
                        if i.a == i.b:
                            ph.append(i)
                        else:
                            m.append(i)

                    if ph:
                        self.showPhantoms(ph, 'f2b967')
                    if m:
                        self.view.add_regions(
                            scopes[2],
                            m,
                            scope='region.orangish',
                            flags=sublime.HIDE_ON_MINIMAP|sublime.DRAW_NO_FILL,
                        )

                if k == 'groups':
                    m  = []
                    ph = []

                    for i in result[k]:
                        if i.a == i.b:
                            ph.append(i)
                        else:
                            m.append(i)

                    if ph:
                        self.showPhantoms(ph, '5897fb')
                    if m:
                        self.view.add_regions(
                            scopes[3],
                            m,
                            scope='region.bluish',
                            flags=sublime.HIDE_ON_MINIMAP,
                        )
                if k == 'annotations':
                    self.view.add_regions(
                        scopes[4],
                        result[k]['regions'],
                        annotations=result[k]['text'],
                        annotation_color='green',
                    )
        if not result['lines']:
            self.view.add_regions(
                scopes[0],
                [sublime.Region(self.view.size(), self.view.size())],
                annotations=['no matches'],
                annotation_color='gray'
            )

    def showPhantoms(self, phantoms, color):
        global ps

        ph = []
        for i in phantoms:
            ph.append(sublime.Phantom(i, '<div  style="background-color:#' + color + ';margin-right:-5px;width:1px;">&nbsp;</div>', sublime.LAYOUT_INLINE))
        ps.update(ph)

    def clearRegions(self):
        global ps, scopes

        for i in scopes:
            self.view.erase_regions(i)

        if ps:
            ps.update([])

    def getRegex(self):
        global scopes
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
                    'scope': scopes[0],
                    'region': sublime.Region(e.pos + 1, e.pos + 2),
                    'icon': 'circle',
                    'annotation': e.msg + ' in pos ' + str(e.pos),
                })
        except Exception as e:
            raise e
        else:
            raise MyExc({
                    'scope': scopes[0],
                    'region': self.view.full_line(0),
                    'annotation': 'regular expression error',
                })

    def getTestLines(self, multiline):
        region = sublime.Region(self.view.full_line(0).b, self.view.size())
        if multiline:
            s = []
            for i in self.view.split_by_newlines(region):
                s.append((i, self.view.substr(i)))
            return s
        else:
            return [(region, self.view.substr(region))]


class RegexMatchViewEventListener(sublime_plugin.ViewEventListener):
    def on_modified_async(self):
        self.view.run_command('regex_match')
    def on_load_async(self):
        self.view.run_command('regex_match')
    def on_reload_async(self):
        self.view.run_command('regex_match')
    def on_activated_async(self):
        self.view.run_command('regex_match')
