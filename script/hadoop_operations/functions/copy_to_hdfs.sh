#!/bin/bash

#########################################
#
#   file name:  copy_to_hdfs.sh
#   function:   copy file from local to hdfs
#   usage:      copy_to_hdfs.sh <src_type> <src_file> <dst_dir>
#
#########################################

if [ $# != 3 ]; then
    echo "##############################################"
    echo "Argments Eroor !!!"
    echo "usage: copy_to_hdfs.sh <src_type> <src_file/dir> <dst_dir>"
    echo "src_type: -d -> directory, -f -> file"
    echo "##############################################"
    exit 1
fi

SRC_TYEP=$1
SRC_PATH=$2
DEST_DIR=$3

# Source file/dir type check
case "${SRC_TYEP}" in
"-f") ;;

"-d") ;;

*)
    echo "##############################################"
    echo "### src_type '${SRC_TYEP}' is wrong !!!"
    echo "### src_type: -d -> directory, -f -> file"
    echo "##############################################"
    exit 1
    ;;
esac

# Source file existance check
if [ "${SRC_TYEP}" = "-f" ]; then
    if [ ! -f "${SRC_PATH}" ]; then
        echo "##############################################"
        echo "### READ Failded !!! (${SRC_PATH})"
        echo "### Check if the src_type is correnct !!! "
        echo "##############################################"
        exit 1
    fi
else
    if [ ! -d "${SRC_PATH}" ]; then
        echo "##############################################"
        echo "### READ Failded !!! (${SRC_PATH})"
        echo "### Check if the src_type is correnct !!! "
        echo "##############################################"
        exit 1
    fi
fi

# Destination directory existance check
hadoop fs -test -d "${DEST_DIR}"
if [ $? -ne 0 ]; then
    echo "Create parent directry[ies]: ${DEST_DIR}"
    hadoop fs -mkdir -p "${DEST_DIR}"

    if [ $? -ne 0 ]; then
        echo "##############################################"
        echo "### Failed to create ${DEST_DIR} !!!"
        echo "##############################################"
        exit 1
    fi

fi

########
# main #
########
hadoop fs -copyFromLocal -f "${SRC_PATH}" "${DEST_DIR}"
if [ $? -ne 0 ]; then
    echo "##############################################"
    echo "### Failded to copy ${SRC_PATH} to ${DEST_DIR} !!!"
    echo "##############################################"
    exit 1
fi

echo "##############################################"
echo "### COMPLETED !!!"
echo "### (copy from ${SRC_PATH} to ${DEST_DIR})"
echo "##############################################"
