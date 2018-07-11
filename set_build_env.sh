if [ "$1" == "" ]; then
  export LD_LIBRARY_PATH=/opt/_internal/cpython-2.7.11-ucs4/lib:${LD_LIBRARY_PATH#/opt/_internal/cpython-2.7.11-ucs2/lib:}
  export PATH=/opt/python/cp27-cp27mu/bin/:${PATH}
  export PYTHON_FLAGS="-DPYTHON_EXECUTABLE:FILEPATH=/opt/python/cp27-cp27mu/bin/python -DPYTHON_INCLUDE_DIR:PATH=/opt/python/cp27-cp27mu/include/python2.7 -DPYTHON_LIBRARIES:FILEPATH=/opt/_internal/cpython-2.7.11-ucs4/lib/libpython2.7.so"
fi


if [ "$1" == "3" ]; then
  export LD_LIBRARY_PATH=/opt/_internal/cpython-2.7.11-ucs4/lib:${LD_LIBRARY_PATH#/opt/_internal/cpython-2.7.11-ucs2/lib:}
  export PATH=/opt/python/cp27-cp27mu/bin/:${PATH}
  export PYTHON_FLAGS="-DPYTHON_EXECUTABLE:FILEPATH=/opt/python/cp27-cp27mu/bin/python -DPYTHON_INCLUDE_DIR:PATH=/opt/python/cp27-cp27mu/include/python2.7 -DPYTHON_LIBRARIES:FILEPATH=/opt/_internal/cpython-2.7.11-ucs4/lib/libpython2.7.so"
fi
