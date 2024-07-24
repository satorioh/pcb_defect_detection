import os


def get_file_paths(directory, is_template=False, suffix='.JPG'):
    """
    获取指定目录下所有以suffix结尾的文件路径。

    :param is_template: 是否模板图片
    :param suffix: 文件后缀名
    :param directory: 目标目录的路径
    :return: 以suffix结尾的图片文件路径列表
    """
    result = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(suffix):
                file_path = os.path.join(root, file)
                label = get_template_label(file) if is_template else get_label(root)
                result.append((file_path, label))
    return result


def get_label(file_path):
    """
    从文件路径中提取标签。

    :param file_path: 文件路径
    :return: 标签
    """
    last_segment = os.path.basename(file_path)
    segment_list = last_segment.split('_')
    if len(segment_list) > 3:
        return "_".join(segment_list[-2:])
    else:
        return segment_list[-1]


def get_template_label(file):
    return file.split('.')[0]
