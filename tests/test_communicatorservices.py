import pytest
import asyncio
from unittest.mock import Mock, patch

from cuemsutils.tools.CommunicatorServices import NngRequestResponse, Communicator

class TestNngRequestResponse:
    """Test the NngRequestResponse class."""
    
    @pytest.fixture
    def nng_rr(self):
        """Create a NngRequestResponse instance for testing."""
        return NngRequestResponse("tcp://127.0.0.1:5555")
    
    def test_initialization_requester_dials_true(self):
        """Test initialization with requester_dials=True."""
        nng = NngRequestResponse("tcp://127.0.0.1:5555", requester_dials=True)
        
        assert nng.address == "tcp://127.0.0.1:5555"
        assert nng.params_request == {'dial': 'tcp://127.0.0.1:5555'}
        assert nng.params_reply == {'listen': 'tcp://127.0.0.1:5555'}
    
    def test_initialization_requester_dials_false(self):
        """Test initialization with requester_dials=False."""
        nng = NngRequestResponse("tcp://127.0.0.1:5555", requester_dials=False)
        
        assert nng.address == "tcp://127.0.0.1:5555"
        assert nng.params_request == {'listen': 'tcp://127.0.0.1:5555'}
        assert nng.params_reply == {'dial': 'tcp://127.0.0.1:5555'}


class TestCommunicator:
    """Test the Communicator class."""
    
    def test_initialization_with_ipc_prefix(self):
        """Test initialization with address that already has ipc:// prefix."""
        with patch('cuemsutils.tools.CommunicatorServices.check_path'):
            comm = Communicator("ipc:///tmp/test.sock")
            
            assert comm.address == "ipc:///tmp/test.sock"
            assert comm.requester_dials == True
    
    def test_initialization_without_ipc_prefix(self):
        """Test initialization with address that needs ipc:// prefix."""
        with patch('cuemsutils.tools.CommunicatorServices.check_path'):
            comm = Communicator("/tmp/test.sock")
            
            assert comm.address == "ipc:///tmp/test.sock"
            assert comm.requester_dials == True
    
    def test_initialization_with_custom_service(self):
        """Test initialization with custom communicator service."""
        mock_service = Mock()
        
        with patch('cuemsutils.tools.CommunicatorServices.check_path'):
            comm = Communicator("/tmp/test.sock", communicator_service=mock_service, requester_dials=False)
            
            assert comm.address == "ipc:///tmp/test.sock"
            assert comm.requester_dials == False
            mock_service.assert_called_once_with("ipc:///tmp/test.sock", requester_dials=False)
    
    def test_communicator_has_required_methods(self):
        """Test that Communicator has all required async methods."""
        with patch('cuemsutils.tools.CommunicatorServices.check_path'):
            comm = Communicator("/tmp/test.sock")
            
            # Check that all required methods exist and are callable
            assert hasattr(comm, 'send_request')
            assert hasattr(comm, 'reply')
            assert hasattr(comm, 'responder_connect')
            assert hasattr(comm, 'responder_get_request')
            assert hasattr(comm, 'responder_post_reply')
            
            # Check that they are async methods
            assert asyncio.iscoroutinefunction(comm.send_request)
            assert asyncio.iscoroutinefunction(comm.reply)
            assert asyncio.iscoroutinefunction(comm.responder_connect)
            assert asyncio.iscoroutinefunction(comm.responder_get_request)
            assert asyncio.iscoroutinefunction(comm.responder_post_reply)
