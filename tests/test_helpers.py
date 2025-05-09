import os
from datetime import datetime
from re import match, Match

from cuemsutils.helpers import ensure_items, extract_items, new_uuid, new_datetime, DATETIME_FORMAT, Uuid, check_path

def test_ensure_items():
    ## ARRANGE
    call_a = lambda: 0
    x = {'a': 1, 'b': 2}
    required = {'a': 0, 'b': 0, 'c': None, 'd': call_a, 'e': ''}

    ## ACT
    target = ensure_items(x, required)

    ## ASSERT
    assert target == {'a': 1, 'b': 2, 'c': None, 'd': 0, 'e': ''}

def test_extract_items():
    ## ARRANGE
    x = {'a': 1, 'b': 2, 'c': 3}
    keys = ['a', 'c']

    ## ACT
    target = extract_items(x.items(), keys)

    ## ASSERT
    assert target == {'a': 1, 'c': 3}.items()

def test_datetime():
    ## ARRANGE
    actual_datetime = datetime.now()
    actual_datetime = actual_datetime.strftime(DATETIME_FORMAT)

    ## ACT
    target_datetime = new_datetime()

    ## ASSERT
    if actual_datetime != target_datetime:
        # Allow for last digit to be different (next second case)
        assert actual_datetime[:-1] == target_datetime[:-1]
    else:
        assert actual_datetime == target_datetime

def test_new_uuid():
    ## ARRANGE
    uuid_regex = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'

    ## ACT
    target_uuid = new_uuid()
    match_uuid = match(uuid_regex, target_uuid())

    ## ASSERT
    assert match_uuid is not None
    assert type(match_uuid) is Match
    assert match_uuid.string == str(target_uuid)
    assert match_uuid.pos == 0
    assert match_uuid.endpos == 36
    assert target_uuid.check() is True

def test_given_uuid():
    ## ARRANGE
    uuid = '123e4567-e89b-42d3-a456-426614174000'
    not_uuid4 = '123e4567-e89b-22d3-a456-426614174000'

    ## ACT
    target_uuid = Uuid(uuid)
    try:
        failed_uuid = Uuid(not_uuid4)
    except ValueError as e:
        failed_uuid = e
    
    ## ASSERT
    assert target_uuid.uuid == uuid
    assert target_uuid.check() is True
    assert str(target_uuid) == uuid
    assert target_uuid() == uuid
    assert type(failed_uuid) is ValueError
    assert str(failed_uuid) == f'uuid {not_uuid4} is not valid'

class TestCheckPath:
    own_path = os.path.abspath(__file__)
    root_path = '/root/.ssh'
    tmp_dir = os.path.join('/', 'tmp', 'cuemsutils')

    def true_or_error(self, path, dir_only = False):
        try:
            check_path(path, dir_only)
        except Exception as e:
            return e
        return True

    def test_check_path_complete(self):
        ## ARRANGE
        fail_path = self.own_path + 'fail'

        ## ACT
        own_path_result = self.true_or_error(self.own_path)
        fail_path_result = self.true_or_error(fail_path)
        dir_path_result = self.true_or_error(fail_path, dir_only=True)

        ## ASSERT
        assert own_path_result is True
        assert dir_path_result is True
        assert isinstance(fail_path_result, Exception)
        assert isinstance(fail_path_result, FileNotFoundError)
        
    def test_check_root_path(self):
        ## ARRANGE
        parent_dir = os.path.dirname(self.root_path)

        ## ACT
        target = self.true_or_error(self.root_path)

        ## ASSERT
        assert isinstance(target, Exception)
        assert isinstance(target, PermissionError)
        assert str(target) == f"Directory {parent_dir} is not readable"

    def test_tmp_dir(self):
        ## ARRANGE
        os.makedirs(self.tmp_dir)

        ## ACT
        target = self.true_or_error(self.tmp_dir)

        ## ASSERT
        assert target is True

        ## CLEANUP
        os.rmdir(self.tmp_dir)

    def test_tmp_file(self):
        ## ARRANGE
        tmp_file = os.path.join(self.tmp_dir, 'test.txt')
        os.makedirs(self.tmp_dir, mode=0o444)

        ## ACT
        target = self.true_or_error(tmp_file)

        ## ASSERT
        assert isinstance(target, Exception)
        assert isinstance(target, PermissionError)
        assert str(target) == f"Directory {self.tmp_dir} is not writable"

        ## CLEANUP
        os.rmdir(self.tmp_dir)
        
        
