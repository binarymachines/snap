#!/usr/bin/env python



class UserEntry():
    def __init__(self, data):
        self.result = data.strip()
        self.is_empty = False
        if not self.result:
            self.is_empty = True



class InputPrompt():
    def __init__(self, prompt_string, default_value=''):
        if default_value:
            self.prompt = '>> %s [%s]: ' % (prompt_string, default_value)
        else:
            self.prompt = '>> %s: ' % prompt_string
        self.default = default_value

    def show(self):
        result = input(self.prompt).strip()
        if not result:
            result = self.default
        return result


class MenuPrompt(object):
    def __init__(self, prompt_string, menu_option_array):
        #self.choice = None
        self.menu_options = menu_option_array
        self.prompt = prompt_string

    def is_valid_selection(self, index):
        try:
            selection_number = int(index)
            if selection_number <= len(self.menu_options) and selection_number > 0:
                return True
            return False
        except ValueError:
            return False


    def display_menu(self):
        print('%s:' % self.prompt)
        opt_id = 1
        for opt in self.menu_options:
            print('  [%d]...%s' % (opt_id, opt['label']))
            opt_id += 1


    def show(self):
        result = None
        self.display_menu()
        while True:
            selection_index = input('> enter selection: ').strip()
            if not selection_index:
                break
            if self.is_valid_selection(selection_index):
                result = self.menu_options[int(selection_index) - 1]['value']
                break
            print('Invalid selection. Please select one of the displayed options.')
            self.display_menu()

        return result


class OptionPrompt(object):
    def __init__(self, prompt_string, options, default_value=''):
        self.prompt_string = prompt_string
        self.default_value = default_value
        self.options = options
        self.result = None

    def show(self):
        display_options = []
        for o in self.options:
            if o == self.default_value:
                display_options.append('[%s]' % o.upper())
            else:
                display_options.append(o)

        prompt_text = '%s %s  : ' % (self.prompt_string, ','.join(display_options))
        result = input(prompt_text).strip()

        if not result: # user did not choose a value
            result = self.default_value

        return result



class Notifier():
    def __init__(self, prompt_string, info_string):
        self.prompt = prompt_string
        self.info = info_string

    def show(self):
        print('[%s]: %s' % (self.prompt, self.info))
