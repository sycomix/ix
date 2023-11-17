import aiofiles
import pytest

from ix.commands.filesystem import (
    write_to_file,
    append_to_file,
    delete_file,
    read_file,
    find_files,
    awrite_to_file,
)


class TestWriteToFile:
    def test_write_to_file(self, tmp_path):
        file_path = tmp_path / "test.txt"
        content = "Hello, world!"
        write_to_file(str(file_path), content)
        assert file_path.exists()
        with open(file_path, "r") as f:
            assert f.read() == content

    def test_write_to_existing_file(self, tmp_path):
        file_path = tmp_path / "test.txt"
        content1 = "Hello, world!"
        content2 = "Goodbye, world!"
        write_to_file(str(file_path), content1)
        write_to_file(str(file_path), content2)
        with open(file_path, "r") as f:
            assert f.read() == content2

    def test_write_to_new_workdir(self, mocker, tmp_path):
        """Test that workdir is created if it does not exist"""
        mock_workdir = tmp_path / "workdir"
        mocker.patch("ix.commands.filesystem.WORKDIR", mock_workdir)
        content = "Hello, world!"
        file_path = "test.txt"
        expected_path = mock_workdir / file_path
        write_to_file(file_path, content)
        assert expected_path.exists()
        with open(expected_path, "r") as f:
            assert f.read() == content


class TestAWriteToFile:
    @pytest.mark.asyncio
    async def test_write_to_file(self, tmp_path):
        file_path = tmp_path / "test.txt"
        content = "Hello, world!"
        await awrite_to_file(str(file_path), content)
        assert file_path.exists()
        async with aiofiles.open(file_path, "r") as f:
            assert await f.read() == content

    @pytest.mark.asyncio
    async def test_write_to_existing_file(self, tmp_path):
        file_path = tmp_path / "test.txt"
        content1 = "Hello, world!"
        content2 = "Goodbye, world!"
        await awrite_to_file(str(file_path), content1)
        await awrite_to_file(str(file_path), content2)
        async with aiofiles.open(file_path, "r") as f:
            assert await f.read() == content2

    @pytest.mark.asyncio
    async def test_write_to_new_workdir(self, mocker, tmp_path):
        """Test that workdir is created if it does not exist"""
        mock_workdir = tmp_path / "workdir"
        mocker.patch("ix.commands.filesystem.WORKDIR", mock_workdir)
        content = "Hello, world!"
        file_path = "test.txt"
        expected_path = mock_workdir / file_path
        await awrite_to_file(str(expected_path), content)
        async with aiofiles.open(expected_path, "r") as f:
            assert await f.read() == content


class TestAppendToFile:
    def test_append_to_file(self, tmp_path):
        file_path = tmp_path / "test.txt"
        content = "Hello, world!"
        append_to_file(str(file_path), content)
        assert file_path.exists()
        with open(file_path, "r") as f:
            assert f.read() == content

    def test_append_to_existing_file(self, tmp_path):
        file_path = tmp_path / "test.txt"
        content1 = "Hello, world!"
        content2 = "Goodbye, world!"
        with open(file_path, "w") as f:
            f.write(content1)
        append_to_file(str(file_path), content2)
        with open(file_path, "r") as f:
            assert f.read() == content1 + content2


class TestDeleteFile:
    def test_delete_file(self, tmp_path):
        file_path = tmp_path / "test.txt"
        content = "Hello, world!"
        with open(file_path, "w") as f:
            f.write(content)
        assert file_path.exists()
        delete_file(str(file_path))
        assert not file_path.exists()

    def test_delete_nonexistent_file(self, tmp_path):
        file_path = tmp_path / "test.txt"
        with pytest.raises(FileNotFoundError):
            delete_file(str(file_path))


class TestReadFile:
    def test_read_file(self, tmp_path):
        file_path = tmp_path / "test.txt"
        content = "Hello, world!"
        with open(file_path, "w") as f:
            f.write(content)
        assert read_file(str(file_path)) == content

    def test_read_nonexistent_file(self, tmp_path):
        file_path = tmp_path / "test.txt"
        with pytest.raises(FileNotFoundError):
            read_file(str(file_path))


class TestFindFiles:
    def test_find_all_files(self, tmp_path):
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()
        file_paths = []
        for i in range(3):
            file_path = dir_path / f"file_{i}.txt"
            with open(file_path, "w") as f:
                f.write("test")
            file_paths.append(str(file_path))
        results = find_files(str(dir_path / "*"))
        assert len(results) == 3
        assert all(result in file_paths for result in results)

    def test_find_files_with_no_matches(self, tmp_path):
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()
        results = find_files(str(dir_path / "*.txt"))
        assert len(results) == 0
