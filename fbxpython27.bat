@echo off
pushd %~dp0
    set PYTHONPATH=C:\Program Files\Autodesk\FBX\FBX Python SDK\2019.0\lib\Python27_x86
    C:\Python27\Python.exe %*
popd
