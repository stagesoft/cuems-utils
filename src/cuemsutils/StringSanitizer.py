class StringSanitizer():
    """Ensure that the string is sanitized and safe for use in the system"""
    @staticmethod
    def sanitize_text_size(_string):
        
        if _string and (len(_string) > 65535):
            _string = _string[0:65534] # return frist 255 characters
        return _string

    @staticmethod
    def sanitize_name(_string): #TODO: scape characters?
        if len(_string) > 255 :
            _string = _string[0:254] # return frist 255 characters
        return _string
    
    @staticmethod
    def sanitize_file_name(_string):
        if len(_string) >= 240 :
            _string = _string[0:236] + _string[-4:] # return frist 236 characters + last 4 chars = total 240 of max 255. Leave room for versioning and .tmp

        _string = _string.replace(' ', '_')
        _string = _string.replace('-', '_')
        keepcharacters = ('.','_')
        return "".join(c for c in _string if c.isalnum() or c in keepcharacters).rstrip().lower()

    @staticmethod
    def sanitize_dir_name(_string):
        if len(_string) >= 240 :
            _string = _string[0:236] + _string[-4:] # return frist 236 characters + last 4 chars = total 240 of max 255. Leave room for versioning and .tmp

        _string = _string.replace(' ', '_')
        _string = _string.replace('-', '_')
        keepcharacters = ('_')
        return "".join(c for c in _string if c.isalnum() or c in keepcharacters).rstrip().lower()
    
    @staticmethod
    def sanitize_dir_permit_increment(_string):
        if len(_string) >= 240 :
            _string = _string[0:236] + _string[-4:] # return frist 236 characters + last 4 chars = total 240 of max 255. Leave room for versioning and .tmp

        _string = _string.replace(' ', '_')
        keepcharacters = ('_', '-')
        return "".join(c for c in _string if c.isalnum() or c in keepcharacters).rstrip().lower()
