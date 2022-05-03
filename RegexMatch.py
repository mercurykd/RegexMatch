import sublime
import sublime_plugin
import re

class StartRegexMatchCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view.window().new_file()
        view.set_name('Regex Match')
        view.assign_syntax('scope:source.regex')
        view.insert(edit, 0, '~~')
        sel = view.sel()
        sel.clear()
        sel.add(sublime.Region(1, 1))
        view.set_scratch(True)

class RegexMatchCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        try:
            # clean regions
            self.view.erase_regions('error_reg')
            self.view.erase_regions('green')
            self.view.erase_regions('match')
            self.view.erase_regions('groups')
            self.view.erase_regions('annotations')
            s = []
            multiline = False
            rc = False
            lines = enumerate(self.view.split_by_newlines(sublime.Region(0, self.view.size())))
            for k, i in lines:
                if k == 0:
                    reg = self.view.substr(i)
                else:
                    s.append((i, self.view.substr(i)))
            s_all = sublime.Region(self.view.full_line(0).b, self.view.size())
            if self.view.substr(s_all):
                s_all = (s_all, self.view.substr(s_all))
            else:
                s_all = []

            # check reg
            r = re.match(r'(.)(.+)\1(.+)?', reg)
            if r:
                regex = r.group(2)
                flags = r.group(3)
                fl = 0
                try:
                    if flags:
                        for i in flags:
                            if i == 'i':
                                fl = fl | re.I
                            elif i == 's':
                                fl = fl | re.S
                            elif i == 'u':
                                fl = fl | re.U
                            elif i == 'm':
                                fl = fl | re.M
                                multiline = True
                            else:
                                raise re.error('not supported flag "' + i + '"', pos = r.group(0).rfind(i) - 1)
                    rc = re.compile(regex, fl)
                except Exception as e:
                    e.pos += 1
                    self.view.add_regions(
                        'error_reg',
                        [sublime.Region(e.pos, e.pos + 1)],
                        scope='region.redish',
                        icon='circle',
                        annotations=[e.msg + ' in pos ' + str(e.pos)]
                    )
            else:
                self.view.add_regions(
                    'error_reg',
                    [self.view.full_line(0)],
                    scope='region.redish',
                    annotations=['error regular expression']
                )

            # build string's
            if not multiline and s_all:
                s = [s_all]

            if rc and s:
                ok_r = []
                ok_a = {
                    'region' : [],
                    'annotation' : [],
                }
                ok_m = []
                ok_d = []
                ok_g = []
                for r, t in s:
                    c = 0
                    an = []
                    for i, m in enumerate(rc.finditer(t)):
                        c += 1
                        match = m.group(0)
                        ok_r.append(r)
                        ok_m.append(sublime.Region(r.a + m.start(), r.a + m.end()))
                        an.append('<br>match ' + str(i + 1) + ': ' + match)
                        for k, g in enumerate(m.groups()):
                            if g:
                                ok_g.append(sublime.Region(r.a + m.start() + match.find(g), r.a + m.start() + match.find(g) + len(g)))
                                an.append(str(k + 1) + ': ' + g)
                        gd = m.groupdict()
                        for g in gd:
                            if g:
                                ok_g.append(sublime.Region(r.a + m.start() + match.find(gd[g]), r.a + m.start() + match.find(gd[g]) + len(gd[g])))
                                an.append(str(g) + ': ' + gd[g])
                    if c:
                        an.insert(0, 'matches ' + str(c))
                        ok_a['annotation'].append('<br>'.join(an))
                        ok_a['region'].append(r)


                if ok_r:
                    self.view.add_regions(
                        'green',
                        ok_r,
                        scope='region.greenish',
                        icon='dot',
                        flags=sublime.HIDE_ON_MINIMAP|sublime.DRAW_NO_FILL,
                    )
                else:
                    self.view.add_regions(
                        'error_reg',
                        [sublime.Region(self.view.size(), self.view.size())],
                        annotations=['no matches'],
                        annotation_color='gray'
                    )
                if ok_a:
                    self.view.add_regions(
                        'annotations',
                        ok_a['region'],
                        annotations=ok_a['annotation'],
                        annotation_color='green'
                    )
                if ok_m:
                    self.view.add_regions(
                        'match',
                        ok_m,
                        scope='region.orangish',
                        flags=sublime.HIDE_ON_MINIMAP|sublime.DRAW_NO_FILL,
                    )
                if ok_g:
                    self.view.add_regions(
                        'groups',
                        ok_g,
                        scope='region.bluish',
                        flags=sublime.HIDE_ON_MINIMAP,
                    )
        except Exception as e:
            self.view.add_regions(
                'error_reg',
                [sublime.Region(self.view.size(), self.view.size())],
                scope='region.redish',
                annotations=['plugin error, see console']
            )
            raise e

class RegexMatchViewEventListener(sublime_plugin.ViewEventListener):
    def on_modified_async(self):
        if self.view.syntax().scope == 'source.regex':
            self.view.run_command('regex_match')
    def on_load_async(self):
        if self.view.syntax().scope == 'source.regex':
            self.view.run_command('regex_match')
    def on_reload_async(self):
        if self.view.syntax().scope == 'source.regex':
            self.view.run_command('regex_match')
    def on_activated_async(self):
        if self.view.syntax().scope == 'source.regex':
            self.view.run_command('regex_match')
