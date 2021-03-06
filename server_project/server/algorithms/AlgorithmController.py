import os
from algorithms.IAlgorithmController import IAlgorithmController
from algorithms.models import Algorithm, Tag, TagList
from build_bot_project.build_bot import BuildBot
from build_bot_project.languages.cpp_language import CPPLanguage
from build_bot_project.languages.cs_language import CSLanguage
from build_bot_project.languages.fp_language import FPLanguage
from common.cmd_utils import STATUS_SUCCESS, STATUS_ERROR_LANGUAGE_NOT_FOUND
from test_bot_project.test_bot import TestBot


class AlgorithmController(IAlgorithmController):
    def __init__(self, config_parser):
        IAlgorithmController.__init__(self)
        self.build_bot = BuildBot()
        self.test_bot = TestBot()
        self.config_parser = config_parser
        self.work_dir = self.config_parser.get("general", "work_dir")

    def remove_algorithm(self, name):
        current_algorithm = Algorithm.objects.filter(name=name).get()
        # TODO: add full delete: remove status and test data
        # current_algorithm.status_id.delete()
        # current_algorithm.test_data_id.delete()
        current_algorithm.delete()

    def get_algorithm(self, name):
        # Algorithm.objects.filter(name=name).first()
        return Algorithm.objects.filter(name=name).get()

    def add_algorithm(self, algorithm):
        try:
            (ret_code, out, err) = self._build_algorithm(algorithm)
        except WindowsError:
            self.remove_algorithm(algorithm.name)
            raise

        if ret_code != STATUS_SUCCESS:
            self.remove_algorithm(algorithm.name)

        return ret_code, out, err

    def run_algorithm(self, name):
        algorithm = self.get_algorithm(name)
        exe_path = self._get_exe_path(algorithm)
        return self.test_bot.run(file=exe_path,
                                 run_string=algorithm.testdata_id.run_options)

    def search_algorithm(self, name):
        return Algorithm.objects.get(name__iregex=r'\y{0}\y'.format(name)).get()

    def get_algorithms_list(self):
        return Algorithm.objects.all()

    def get_tagged_algorithms_list(self, tag):
        tag_db = Tag.objects.filter(tag_name=tag).all()
        # tagged_algorithm_ids = TagList.objects.filter(tag_id=tag_db).all()
        tagged_algorithms = Algorithm.objects.filter(
            algorithm_id__in=TagList.objects.filter(tag_id=tag_db).values_list('algorithm_id'))

        return tagged_algorithms

    def get_algorithm_names_list(self):
        alg_obj_list = self.get_algorithms_list()
        result = []
        for item in alg_obj_list:
            result.append(item.name)
        return result

    def get_tagged_algorithm_names_list(self, tag):
        alg_obj_list = self.get_tagged_algorithms_list(tag)
        result = []
        for item in alg_obj_list:
            result.append(item.name)
        return result

    def update_algorithm(self,
                         name,
                         description,
                         source_code,
                         build_options,
                         testdata_id,
                         price,
                         language,
                         tags):
        old_algorithm = self.get_algorithm(name)
        algorithm = self.get_algorithm(name)

        algorithm.user_id = old_algorithm.user_id
        algorithm.status_id = old_algorithm.status_id

        algorithm.name = name
        algorithm.description = description
        algorithm.source_code = source_code
        algorithm.build_options = build_options
        algorithm.testdata_id = testdata_id
        algorithm.price = price
        algorithm.language = language

        old_tags_list = TagList.objects.filter(algorithm_id=algorithm).all()
        old_tags_list.delete()

        all_tags = Tag.objects.all()
        for tag in all_tags:
            try:
                TagList.objects.filter(tag_id=tag).all()
            except TagList.DoesNotExist:
                tag.delete()

        for tag in tags:
            db_tag = ""

            try:
                db_tag = Tag.objects.filter(tag_name=tag.strip()).get()
            except Tag.DoesNotExist:
                db_tag = Tag.objects.create(tag_name=tag.strip())
                db_tag.save()

            algorithm_tag = TagList.objects.create(tag_id=db_tag,
                                                   algorithm_id=algorithm)
            algorithm_tag.save()

        (ret_code, out, err) = self._build_algorithm(algorithm)
        if ret_code == STATUS_SUCCESS:
            algorithm.save()
        return ret_code

    @staticmethod
    def get_languages_list():
        return [CPPLanguage.get_name(), CSLanguage.get_name(), FPLanguage.get_name()]

    @staticmethod
    def create_algorithm(name,
                         description,
                         source_code,
                         build_options,
                         testdata_id,
                         price,
                         user_id,
                         status_id,
                         language,
                         tags):

        algorithm = Algorithm.objects.create(name=name,
                                             description=description,
                                             source_code=source_code,
                                             build_options=build_options,
                                             testdata_id=testdata_id,
                                             price=price, user_id=user_id,
                                             status_id=status_id,
                                             language=language)

        algorithm.save()

        for tag in tags:
            db_tag = ""

            try:
                db_tag = Tag.objects.filter(tag_name=tag.strip()).get()
            except Tag.DoesNotExist:
                db_tag = Tag.objects.create(tag_name=tag.strip())
                db_tag.save()

            algorithm_tag = TagList.objects.create(tag_id=db_tag,
                                                   algorithm_id=algorithm)
            algorithm_tag.save()

        return algorithm

    def _get_algorithm_dir(self, algorithm):
        return self.work_dir + os.sep + str(algorithm.user_id.user_id) + os.sep + str(algorithm.algorithm_id)

    def _get_exe_path(self, algorithm):
        return self._get_algorithm_dir(algorithm) + os.sep + algorithm.name + ".exe"

    def _build_algorithm(self, algorithm):
        if algorithm.language == CPPLanguage.get_name():
            language = CPPLanguage(self.config_parser)
        elif algorithm.language == CSLanguage.get_name():
            language = CSLanguage(self.config_parser)
        elif algorithm.language == FPLanguage.get_name():
            language = FPLanguage(self.config_parser)
        else:
            return [STATUS_ERROR_LANGUAGE_NOT_FOUND, "", ""]

        self.build_bot.set_language(language)

        algorithm_dir = self._get_algorithm_dir(algorithm)
        if not os.path.exists(algorithm_dir):
            os.makedirs(algorithm_dir)

        source_file = algorithm_dir + os.sep + algorithm.name + "." + language.get_extension()

        with open(source_file, "wb") as src_file:
            src_file.write(algorithm.source_code)

        exe_path = self._get_exe_path(algorithm)

        return self.build_bot.build(source_file, str(exe_path))





