from cuemsutils.xml.Parsers import GenericParser, OutputsParser

class DmxSceneParser(GenericParser):
    pass

    def parse(self):
        for class_string, class_item_list in self.init_dict.items():   
            for class_item in class_item_list:
                parser_class, class_string = self.get_parser_class(class_string)
                item_obj = parser_class(init_dict=class_item, class_string=class_string).parse()
                self.item_gp.set_universe(item_obj, class_item['id'])
        return self.item_gp

class AudioCueOutputParser(OutputsParser):
    pass

class VideoCueOutputParser(OutputsParser):
    pass
class DmxCueOutputParser(OutputsParser):
    pass

class CuemsNodeParser(GenericParser):
    pass
