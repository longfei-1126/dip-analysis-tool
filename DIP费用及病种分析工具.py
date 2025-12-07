# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 设置页面配置（必须放在最前面）
st.set_page_config(
    page_title="DIP病种分析工具",
    page_icon="🏥"或 page_icon="📊"
    layout="wide",
    initial_sidebar_state="expanded"
)


# 创建默认的南充市DIP病种及分值目录库4.0版数据
def create_default_dip_database():
    data = {
        '序号': [4],
        'DIP编码': ['H25.0S002'],
        'DIP名称': ['老年性初期白内障-手术组02'],
        '病种类型': ['基层病种'],
        '诊断编码': ['H25.0'],
        '诊断名称': ['老年性初期白内障'],
        '操作编码': ['13.4100x001'],
        '操作名称': ['白内障超声乳化抽吸术'],
        '病例数': [7568],
        '入组的DIP基准分值': [78.0521]
    }
    return pd.DataFrame(data)


# 创建默认的手术操作分类代码国家临床版3.0目录数据
def create_default_surgery_database():
    data = {
        '操作编码': ['13.4100x001'],
        '操作名称': ['白内障超声乳化抽吸术'],
        '操作类别': ['手术']
    }
    return pd.DataFrame(data)


# 创建默认的诊断编码及名称（医保2020版）目录数据
def create_default_diagnosis_database():
    data = {
        '诊断编码': ['H25.0', 'I10.x00', 'I11.900', 'I20.000', 'I21.900',
                     'J18.900', 'J44.900', 'K35.900', 'N17.900', 'R50.900'],
        '诊断名称': ['老年性初期白内障', '特发性(原发性)高血压', '高血压性心脏病', '不稳定型心绞痛',
                     '急性心肌梗死', '肺炎', '慢性阻塞性肺病', '急性阑尾炎', '急性肾衰竭', '发热']
    }
    return pd.DataFrame(data)


# 初始化session state
if 'dip_base_score_input' not in st.session_state:
    st.session_state.dip_base_score_input = 27.7173  # 默认值

if 'dip_base_score_slider' not in st.session_state:
    st.session_state.dip_base_score_slider = 27.7173  # 默认值

if 'dip_database' not in st.session_state:
    st.session_state.dip_database = create_default_dip_database()

if 'surgery_database' not in st.session_state:
    st.session_state.surgery_database = create_default_surgery_database()

if 'diagnosis_database' not in st.session_state:
    st.session_state.diagnosis_database = create_default_diagnosis_database()

if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None

if 'uploaded_surgery_file' not in st.session_state:
    st.session_state.uploaded_surgery_file = None

if 'uploaded_diagnosis_file' not in st.session_state:
    st.session_state.uploaded_diagnosis_file = None

if 'file_processed' not in st.session_state:
    st.session_state.file_processed = False

if 'surgery_file_processed' not in st.session_state:
    st.session_state.surgery_file_processed = False

if 'diagnosis_file_processed' not in st.session_state:
    st.session_state.diagnosis_file_processed = False

if 'show_group_info' not in st.session_state:
    st.session_state.show_group_info = False

if 'selected_diagnosis' not in st.session_state:
    st.session_state.selected_diagnosis = None

if 'selected_operation' not in st.session_state:
    st.session_state.selected_operation = None

if 'custom_operation_input' not in st.session_state:
    st.session_state.custom_operation_input = ""

if 'custom_diagnosis_input' not in st.session_state:
    st.session_state.custom_diagnosis_input = ""


# 新增函数：将NaN值替换为中文"无"
def replace_nan_with_chinese(value):
    """将NaN、None或空值替换为中文'无'"""
    if pd.isna(value) or value is None or value == "":
        return "无"
    return value


# 新增函数：处理诊断编码，截取到小数点后第一位
def truncate_diagnosis_code(diagnosis_code):
    """处理诊断编码，截取到小数点后第一位"""
    if not diagnosis_code or diagnosis_code == "无":
        return ""

    # 如果编码中包含小数点
    if '.' in diagnosis_code:
        parts = diagnosis_code.split('.')
        if len(parts) >= 2:
            # 截取小数点后第一位
            decimal_part = parts[1][:1] if len(parts[1]) > 0 else ""
            return f"{parts[0]}.{decimal_part}"

    # 如果没有小数点，返回原编码
    return diagnosis_code


# 新增函数：在诊断目录中查找诊断编码
def find_diagnosis_code(diagnosis_input):
    """在诊断目录中查找诊断编码"""
    if not diagnosis_input or diagnosis_input == "无":
        return None

    # 首先检查输入是否是诊断编码格式（包含字母和数字）
    # 假设诊断编码以字母开头
    if diagnosis_input[0].isalpha() and any(char.isdigit() for char in diagnosis_input):
        # 可能是诊断编码，直接使用
        return diagnosis_input

    # 否则按诊断名称查找
    matching_records = st.session_state.diagnosis_database[
        st.session_state.diagnosis_database['诊断名称'] == diagnosis_input
        ]

    if not matching_records.empty:
        return matching_records.iloc[0]['诊断编码']

    return None


# 新增函数：在DIP数据库中查找匹配的诊断记录
def find_matching_diagnosis(truncated_diagnosis_code):
    """在DIP数据库中查找匹配的诊断记录"""
    if not truncated_diagnosis_code:
        return None

    # 在DIP数据库中查找匹配的诊断编码
    matching_records = st.session_state.dip_database[
        st.session_state.dip_database['诊断编码'] == truncated_diagnosis_code
        ]

    if not matching_records.empty:
        return matching_records.iloc[0]

    return None


# 新增函数：在DIP数据库中查找匹配的操作记录
def find_matching_operation(diagnosis_code, operation_input):
    """在DIP数据库中查找匹配的操作记录"""
    if not operation_input or operation_input == "无":
        return None

    # 首先尝试匹配操作编码
    matching_records = st.session_state.dip_database[
        (st.session_state.dip_database['诊断编码'] == diagnosis_code) &
        (st.session_state.dip_database['操作编码'] == operation_input)
        ]

    if not matching_records.empty:
        return matching_records.iloc[0]

    # 如果操作编码不匹配，尝试匹配操作名称
    matching_records = st.session_state.dip_database[
        (st.session_state.dip_database['诊断编码'] == diagnosis_code) &
        (st.session_state.dip_database['操作名称'] == operation_input)
        ]

    if not matching_records.empty:
        return matching_records.iloc[0]

    return None


# 新增函数：在手术操作分类目录中查找操作类别
def find_operation_category(operation_input):
    """在手术操作分类目录中查找操作类别"""
    if not operation_input or operation_input == "无":
        return None

    # 首先尝试匹配操作编码
    matching_records = st.session_state.surgery_database[
        st.session_state.surgery_database['操作编码'] == operation_input
        ]

    if not matching_records.empty:
        return matching_records.iloc[0]['操作类别']

    # 如果操作编码不匹配，尝试匹配操作名称
    matching_records = st.session_state.surgery_database[
        st.session_state.surgery_database['操作名称'] == operation_input
        ]

    if not matching_records.empty:
        return matching_records.iloc[0]['操作类别']

    return None


# 新增函数：根据诊断编码获取病种类型
def get_diagnosis_type(diagnosis_code):
    """根据诊断编码获取病种类型"""
    if not diagnosis_code or diagnosis_code == "无":
        return None

    matching_records = st.session_state.dip_database[
        st.session_state.dip_database['诊断编码'] == diagnosis_code
        ]

    if not matching_records.empty:
        return matching_records.iloc[0]['病种类型']

    return None


# 新增函数：根据诊断编码和操作类别获取综合病种的DIP信息
def get_comprehensive_dip_info(diagnosis_code, operation_category):
    """根据诊断编码和操作类别获取综合病种的DIP信息"""
    if not diagnosis_code or not operation_category:
        return None

    # 根据操作类别确定DIP组别
    if operation_category in ['手术', '介入治疗']:
        dip_suffix = '手术组'
    elif operation_category == '治疗性操作':
        dip_suffix = '治疗组'
    elif operation_category == '诊断性操作':
        dip_suffix = '诊断组'
    else:
        return None

    # 查找匹配的综合病种记录
    matching_records = st.session_state.dip_database[
        (st.session_state.dip_database['诊断编码'] == diagnosis_code) &
        (st.session_state.dip_database['DIP名称'].str.contains(dip_suffix))
        ]

    if not matching_records.empty:
        return matching_records.iloc[0]

    return None


# 新增函数：根据诊断编码获取无操作的DIP信息
def get_diagnosis_only_dip_info(diagnosis_code):
    """根据诊断编码获取无操作的DIP信息（用于基层病种和核心病种）"""
    if not diagnosis_code or diagnosis_code == "无":
        return None

    # 查找诊断编码匹配且操作编码为空的记录
    matching_records = st.session_state.dip_database[
        (st.session_state.dip_database['诊断编码'] == diagnosis_code) &
        ((st.session_state.dip_database['操作编码'] == "无") |
         (st.session_state.dip_database['操作编码'].isna()) |
         (st.session_state.dip_database['操作编码'] == ""))
        ]

    if not matching_records.empty:
        return matching_records.iloc[0]

    return None


def calculate_dip_metrics(
        诊疗费用, 检查检验费用, 药品费用, 耗材费用,
        医疗性收入成本率, 药耗成本率, 统筹基金支付金额,
        入组的DIP基准分值, 医院等级系数, 点值
):
    # 计算入组的DIP分值
    入组的DIP分值 = 入组的DIP基准分值 * 医院等级系数

    # 计算中间指标
    住院总费用 = 诊疗费用 + 检查检验费用 + 药品费用 + 耗材费用
    医疗性收入 = 诊疗费用 + 检查检验费用
    药耗收入 = 药品费用 + 耗材费用
    治疗成本 = 医疗性收入 * 医疗性收入成本率 + 药耗收入 * 药耗成本率
    病人自付金额 = 住院总费用 - 统筹基金支付金额
    DIP支付标准 = 入组的DIP分值 * 点值

    # 根据新的DIP付费办法，DIP核算金额为负数时计算为0
    DIP核算金额 = max(DIP支付标准 - 病人自付金额, 0)

    # 计算目标指标
    病例真实盈亏金额 = DIP支付标准 - 治疗成本
    DIP回款率 = DIP核算金额 / 统筹基金支付金额 if 统筹基金支付金额 != 0 else 0

    # DIP盈亏金额保持不变
    DIP盈亏金额 = DIP核算金额 - 统筹基金支付金额

    return {
        '病例真实盈亏金额': 病例真实盈亏金额,
        'DIP回款率': DIP回款率,
        '住院总费用': 住院总费用,
        '治疗成本': 治疗成本,
        'DIP支付标准': DIP支付标准,
        'DIP核算金额': DIP核算金额,
        'DIP盈亏金额': DIP盈亏金额,
        '入组的DIP分值': 入组的DIP分值
    }


# 创建Streamlit应用
st.title('DIP病种及费用分析工具')

# 添加DIP目录导入功能
st.sidebar.header('DIP目录导入')
uploaded_file = st.sidebar.file_uploader(
    "上传DIP目录文件 (Excel格式)",
    type=['xlsx', 'xls'],
    help="请上传包含DIP目录的Excel文件，文件应包含'诊断名称'、'诊断编码'、'操作名称'、'操作编码'和'入组的DIP基准分值'等列"
)

# 处理上传的DIP目录文件
if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file:
    try:
        # 读取Excel文件
        dip_data = pd.read_excel(uploaded_file)

        # 检查必要的列是否存在
        required_columns = ['诊断名称', '诊断编码', '操作名称', '操作编码', '入组的DIP基准分值']
        missing_columns = [col for col in required_columns if col not in dip_data.columns]

        if missing_columns:
            st.sidebar.error(f"上传的文件缺少必要列: {', '.join(missing_columns)}")
        else:
            # 将NaN值替换为中文"无"
            for col in dip_data.columns:
                if dip_data[col].dtype == 'object':  # 只处理字符串类型的列
                    dip_data[col] = dip_data[col].apply(replace_nan_with_chinese)

            # 更新DIP数据库
            st.session_state.dip_database = dip_data
            st.session_state.uploaded_file = uploaded_file
            st.session_state.file_processed = True
            st.sidebar.success(f"成功导入DIP目录！共 {len(dip_data)} 条记录")

    except Exception as e:
        st.sidebar.error(f"文件读取错误: {str(e)}")
elif uploaded_file is None and st.session_state.uploaded_file is not None:
    # 如果用户删除了上传的文件，恢复为默认数据
    st.session_state.dip_database = create_default_dip_database()
    st.session_state.uploaded_file = None
    st.session_state.file_processed = False

# 添加手术操作分类目录导入功能
st.sidebar.header('手术操作分类目录导入')
uploaded_surgery_file = st.sidebar.file_uploader(
    "上传手术操作分类目录文件 (Excel格式)",
    type=['xlsx', 'xls'],
    help="请上传包含手术操作分类的Excel文件，文件应包含'操作编码'、'操作名称'和'操作类别'等列"
)

# 处理上传的手术操作分类目录文件
if uploaded_surgery_file is not None and uploaded_surgery_file != st.session_state.uploaded_surgery_file:
    try:
        # 读取Excel文件
        surgery_data = pd.read_excel(uploaded_surgery_file)

        # 检查必要的列是否存在
        required_columns = ['操作编码', '操作名称', '操作类别']
        missing_columns = [col for col in required_columns if col not in surgery_data.columns]

        if missing_columns:
            st.sidebar.error(f"上传的文件缺少必要列: {', '.join(missing_columns)}")
        else:
            # 将NaN值替换为中文"无"
            for col in surgery_data.columns:
                if surgery_data[col].dtype == 'object':  # 只处理字符串类型的列
                    surgery_data[col] = surgery_data[col].apply(replace_nan_with_chinese)

            # 更新手术操作分类数据库
            st.session_state.surgery_database = surgery_data
            st.session_state.uploaded_surgery_file = uploaded_surgery_file
            st.session_state.surgery_file_processed = True
            st.sidebar.success(f"成功导入手术操作分类目录！共 {len(surgery_data)} 条记录")

    except Exception as e:
        st.sidebar.error(f"文件读取错误: {str(e)}")
elif uploaded_surgery_file is None and st.session_state.uploaded_surgery_file is not None:
    # 如果用户删除了上传的文件，恢复为默认数据
    st.session_state.surgery_database = create_default_surgery_database()
    st.session_state.uploaded_surgery_file = None
    st.session_state.surgery_file_processed = False

# 添加诊断编码及名称目录导入功能
st.sidebar.header('诊断编码及名称目录导入')
uploaded_diagnosis_file = st.sidebar.file_uploader(
    "上传诊断编码及名称目录文件 (Excel格式)",
    type=['xlsx', 'xls'],
    help="请上传包含诊断编码及名称的Excel文件，文件应包含'诊断编码'和'诊断名称'等列"
)

# 处理上传的诊断编码及名称目录文件
if uploaded_diagnosis_file is not None and uploaded_diagnosis_file != st.session_state.uploaded_diagnosis_file:
    try:
        # 读取Excel文件
        diagnosis_data = pd.read_excel(uploaded_diagnosis_file)

        # 检查必要的列是否存在
        required_columns = ['诊断编码', '诊断名称']
        missing_columns = [col for col in required_columns if col not in diagnosis_data.columns]

        if missing_columns:
            st.sidebar.error(f"上传的文件缺少必要列: {', '.join(missing_columns)}")
        else:
            # 将NaN值替换为中文"无"
            for col in diagnosis_data.columns:
                if diagnosis_data[col].dtype == 'object':  # 只处理字符串类型的列
                    diagnosis_data[col] = diagnosis_data[col].apply(replace_nan_with_chinese)

            # 更新诊断编码及名称数据库
            st.session_state.diagnosis_database = diagnosis_data
            st.session_state.uploaded_diagnosis_file = uploaded_diagnosis_file
            st.session_state.diagnosis_file_processed = True
            st.sidebar.success(f"成功导入诊断编码及名称目录！共 {len(diagnosis_data)} 条记录")

    except Exception as e:
        st.sidebar.error(f"文件读取错误: {str(e)}")
elif uploaded_diagnosis_file is None and st.session_state.uploaded_diagnosis_file is not None:
    # 如果用户删除了上传的文件，恢复为默认数据
    st.session_state.diagnosis_database = create_default_diagnosis_database()
    st.session_state.uploaded_diagnosis_file = None
    st.session_state.diagnosis_file_processed = False

# 侧边栏输入参数
st.sidebar.header('输入参数')

# 根据图片数据设置默认值
col1, col2 = st.sidebar.columns(2)

with col1:
    # 使用数字输入框和滑块结合，提供更精确的控制
    诊疗费用 = st.number_input('诊疗费用', min_value=0.0, max_value=200000.0, value=3936.93, step=100.0)
    # 添加一个滑块用于粗略调整
    诊疗费用_slider = st.slider('诊疗费用(滑块)', 0.0, 200000.0, 诊疗费用, 1000.0)
    # 确保两个输入同步
    if 诊疗费用 != 诊疗费用_slider:
        诊疗费用 = 诊疗费用_slider

    检查检验费用 = st.number_input('检查检验费用', min_value=0.0, max_value=200000.0, value=3348.15, step=100.0)
    检查检验费用_slider = st.slider('检查检验费用(滑块)', 0.0, 200000.0, 检查检验费用, 1000.0)
    if 检查检验费用 != 检查检验费用_slider:
        检查检验费用 = 检查检验费用_slider

    药品费用 = st.number_input('药品费用', min_value=0.0, max_value=200000.0, value=2001.41, step=100.0)
    药品费用_slider = st.slider('药品费用(滑块)', 0.0, 200000.0, 药品费用, 1000.0)
    if 药品费用 != 药品费用_slider:
        药品费用 = 药品费用_slider

    耗材费用 = st.number_input('耗材费用', min_value=0.0, max_value=200000.0, value=3115.78, step=100.0)
    耗材费用_slider = st.slider('耗材费用(滑块)', 0.0, 200000.0, 耗材费用, 1000.0)
    if 耗材费用 != 耗材费用_slider:
        耗材费用 = 耗材费用_slider

    医疗性收入成本率 = st.slider('医疗性收入成本率', 0.0, 1.0, 0.50, 0.01)

with col2:
    药耗成本率 = st.slider('药耗成本率', 0.0, 1.5, 1.00, 0.01)

    # 对统筹基金支付金额也采用数字输入框和滑块结合的方式
    统筹基金支付金额 = st.number_input('统筹基金支付金额', min_value=0.0, max_value=300000.0, value=7657.03, step=100.0)
    统筹基金支付金额_slider = st.slider('统筹基金支付金额(滑块)', 0.0, 300000.0, 统筹基金支付金额, 1000.0)
    if 统筹基金支付金额 != 统筹基金支付金额_slider:
        统筹基金支付金额 = 统筹基金支付金额_slider

    # 添加医院的等级系数，保留4位小数，默认值改为1.0330
    医院等级系数 = st.number_input('医院的等级系数', min_value=0.0, max_value=2.0, value=1.0330, step=0.0001,
                                   format="%.4f")
    医院等级系数_slider = st.slider('医院的等级系数(滑块)', 0.0, 2.0, 医院等级系数, 0.1)
    if 医院等级系数 != 医院等级系数_slider:
        医院等级系数 = 医院等级系数_slider

    # 点值类型选择
    点值类型 = st.selectbox('点值类型', ['居民', '职工'], index=1)

    # 根据点值类型设置默认点值
    if 点值类型 == '居民':
        默认点值 = 63.3253
    else:  # 职工
        默认点值 = 73.6011

    # 点值输入
    点值 = st.number_input('点值', min_value=0.0, max_value=200.0, value=默认点值, step=0.0001, format="%.4f")
    点值_slider = st.slider('点值(滑块)', 0.0, 200.0, 点值, 1.0)
    if 点值 != 点值_slider:
        点值 = 点值_slider

# 智能DIP病种选择
st.sidebar.header('智能DIP病种选择')

# 初始化变量
诊断名称 = st.session_state.dip_database.iloc[0]['诊断名称']
诊断编码 = st.session_state.dip_database.iloc[0]['诊断编码']
操作名称 = st.session_state.dip_database.iloc[0]['操作名称']
操作编码 = st.session_state.dip_database.iloc[0]['操作编码']
入组的DIP基准分值 = st.session_state.dip_database.iloc[0]['入组的DIP基准分值']
DIP编码 = st.session_state.dip_database.iloc[0].get('DIP编码', '无')
DIP名称 = st.session_state.dip_database.iloc[0].get('DIP名称', '无')
病种类型 = st.session_state.dip_database.iloc[0].get('病种类型', '无')

# 确保所有字段都使用"无"而不是"nan"
诊断名称 = replace_nan_with_chinese(诊断名称)
诊断编码 = replace_nan_with_chinese(诊断编码)
操作名称 = replace_nan_with_chinese(操作名称)
操作编码 = replace_nan_with_chinese(操作编码)
DIP编码 = replace_nan_with_chinese(DIP编码)
DIP名称 = replace_nan_with_chinese(DIP名称)
病种类型 = replace_nan_with_chinese(病种类型)

# 传统选择
st.sidebar.subheader("传统选择")

# 添加查询顺序选择
查询顺序 = st.sidebar.radio("查询顺序", ["先诊断后操作", "先操作后诊断"], horizontal=True, key="query_order")

if 查询顺序 == "先诊断后操作":
    col1, col2 = st.sidebar.columns(2)

    with col1:
        # 诊断选择
        诊断列表 = st.session_state.dip_database[['诊断编码', '诊断名称']].drop_duplicates()
        诊断选项 = []

        # 将"手动输入诊断..."放在第一行
        诊断选项.append("手动输入诊断...")

        # 然后添加目录中的诊断选项
        for _, row in 诊断列表.iterrows():
            诊断编码_显示 = replace_nan_with_chinese(row['诊断编码'])
            诊断名称_显示 = replace_nan_with_chinese(row['诊断名称'])
            if 诊断编码_显示 != "无":  # 过滤掉无诊断编码的记录
                诊断选项.append(f"{诊断编码_显示} - {诊断名称_显示}")

        # 设置默认值为"手动输入诊断..."
        default_diagnosis_index = 0

        selected_diagnosis = st.selectbox("选择诊断", 诊断选项, index=default_diagnosis_index, key="diagnosis_select")

        # 如果用户选择了"手动输入诊断..."，显示文本输入框
        if selected_diagnosis == "手动输入诊断...":
            # 使用文本输入框让用户输入诊断名称
            st.session_state.custom_diagnosis_input = st.text_input(
                "输入诊断名称",
                value=st.session_state.custom_diagnosis_input,
                placeholder="例如: 急性心肌梗死 或 I21.9"
            )
        elif selected_diagnosis and selected_diagnosis != "手动输入诊断...":
            # 提取诊断编码（去除"无"的情况）
            诊断编码_传统 = selected_diagnosis.split(" - ")[0]
            if 诊断编码_传统 == "无":
                诊断编码_传统 = ""

            # 根据诊断编码获取对应的诊断名称
            匹配记录 = st.session_state.dip_database[
                st.session_state.dip_database['诊断编码'] == 诊断编码_传统
                ]
            if not 匹配记录.empty:
                诊断记录 = 匹配记录.iloc[0]
                诊断名称_传统 = replace_nan_with_chinese(诊断记录['诊断名称'])

    with col2:
        # 操作选择（根据诊断筛选）
        操作选项 = []

        # 将"手动输入操作..."和"无操作的"放在前面
        操作选项.append("手动输入操作...")
        操作选项.append("无操作的")

        if selected_diagnosis and selected_diagnosis != "手动输入诊断...":
            # 提取诊断编码
            诊断编码_传统 = selected_diagnosis.split(" - ")[0] if " - " in selected_diagnosis else selected_diagnosis
            if 诊断编码_传统 == "无":
                诊断编码_传统 = ""

            if 诊断编码_传统:
                # 筛选有操作编码的记录（去除操作编码为"无"的记录）
                操作列表 = st.session_state.dip_database[
                    (st.session_state.dip_database['诊断编码'] == 诊断编码_传统) &
                    (st.session_state.dip_database['操作编码'] != "无") &
                    (~st.session_state.dip_database['操作编码'].isna()) &
                    (st.session_state.dip_database['操作编码'] != "")
                    ][['操作编码', '操作名称', '病种类型', '入组的DIP基准分值']].drop_duplicates()

                if len(操作列表) > 0:
                    for _, row in 操作列表.iterrows():
                        操作编码_显示 = replace_nan_with_chinese(row['操作编码'])
                        操作名称_显示 = replace_nan_with_chinese(row['操作名称'])
                        病种类型_显示 = replace_nan_with_chinese(row['病种类型'])
                        基准分值_显示 = row['入组的DIP基准分值']

                        # 在下拉选项中直接显示病种类型和基准分值
                        display_text = f"{操作编码_显示} - {操作名称_显示} | 病种类型: {病种类型_显示} | 分值: {基准分值_显示:.4f}"
                        操作选项.append(display_text)

        # 操作选择框
        selected_operation = st.selectbox("选择操作", 操作选项, key="operation_select")

        # 如果用户选择了"手动输入操作..."，显示文本输入框
        if selected_operation == "手动输入操作...":
            # 使用文本输入框让用户输入操作编码或名称
            st.session_state.custom_operation_input = st.text_input(
                "输入操作编码或名称",
                value=st.session_state.custom_operation_input,
                placeholder="例如: 13.4100x001 或 白内障超声乳化抽吸术"
            )

else:  # 先操作后诊断
    col1, col2 = st.sidebar.columns(2)

    with col1:
        # 操作选择
        操作列表 = st.session_state.dip_database[['操作编码', '操作名称']].drop_duplicates()
        操作选项 = []

        # 将"手动输入操作..."和"无操作的"放在前面
        操作选项.append("手动输入操作...")
        操作选项.append("无操作的")

        # 然后添加目录中的操作选项
        for _, row in 操作列表.iterrows():
            操作编码_显示 = replace_nan_with_chinese(row['操作编码'])
            操作名称_显示 = replace_nan_with_chinese(row['操作名称'])
            if 操作编码_显示 != "无":  # 过滤掉无操作编码的记录
                操作选项.append(f"{操作编码_显示} - {操作名称_显示}")

        # 操作选择框
        selected_operation = st.selectbox("选择操作", 操作选项, key="operation_first_select")

        # 如果用户选择了"手动输入操作..."，显示文本输入框
        if selected_operation == "手动输入操作...":
            # 使用文本输入框让用户输入操作编码或名称
            st.session_state.custom_operation_input = st.text_input(
                "输入操作编码或名称",
                value=st.session_state.custom_operation_input,
                placeholder="例如: 13.4100x001 或 白内障超声乳化抽吸术"
            )

    with col2:
        # 诊断选择（根据操作筛选）
        诊断选项 = []

        # 将"手动输入诊断..."放在第一行
        诊断选项.append("手动输入诊断...")

        if selected_operation and selected_operation != "手动输入操作...":
            if selected_operation == "无操作的":
                # 如果是无操作的情况，显示所有有无操作记录的诊断
                诊断列表 = st.session_state.dip_database[
                    (st.session_state.dip_database['操作编码'] == "无") |
                    (st.session_state.dip_database['操作编码'].isna()) |
                    (st.session_state.dip_database['操作编码'] == "")
                    ][['诊断编码', '诊断名称', '病种类型', '入组的DIP基准分值']].drop_duplicates()
            else:
                # 提取操作编码
                操作编码_传统 = selected_operation.split(" - ")[
                    0] if " - " in selected_operation else selected_operation

                if 操作编码_传统 and 操作编码_传统 != "无":
                    诊断列表 = st.session_state.dip_database[
                        st.session_state.dip_database['操作编码'] == 操作编码_传统
                        ][['诊断编码', '诊断名称', '病种类型', '入组的DIP基准分值']].drop_duplicates()

            if len(诊断列表) > 0:
                for _, row in 诊断列表.iterrows():
                    诊断编码_显示 = replace_nan_with_chinese(row['诊断编码'])
                    诊断名称_显示 = replace_nan_with_chinese(row['诊断名称'])
                    病种类型_显示 = replace_nan_with_chinese(row['病种类型'])
                    基准分值_显示 = row['入组的DIP基准分值']

                    # 在下拉选项中直接显示病种类型和基准分值
                    display_text = f"{诊断编码_显示} - {诊断名称_显示} | 病种类型: {病种类型_显示} | 分值: {基准分值_显示:.4f}"
                    诊断选项.append(display_text)

        selected_diagnosis = st.selectbox("选择诊断", 诊断选项, key="diagnosis_second_select")

        # 如果用户选择了"手动输入诊断..."，显示文本输入框
        if selected_diagnosis == "手动输入诊断...":
            # 使用文本输入框让用户输入诊断名称
            st.session_state.custom_diagnosis_input = st.text_input(
                "输入诊断名称",
                value=st.session_state.custom_diagnosis_input,
                placeholder="例如: 急性心肌梗死 或 I21.9"
            )

# 添加查询入组按钮
if st.sidebar.button("查询入组", type="primary"):
    st.session_state.show_group_info = True
    st.session_state.selected_diagnosis = selected_diagnosis
    st.session_state.selected_operation = selected_operation

# 显示入组情况（仅在点击了查询入组按钮后显示）
if st.session_state.show_group_info and (
        st.session_state.selected_diagnosis or st.session_state.custom_diagnosis_input):
    # 处理诊断信息
    if 查询顺序 == "先诊断后操作":
        if st.session_state.selected_diagnosis == "手动输入诊断..." and st.session_state.custom_diagnosis_input:
            # 手动输入诊断模式
            诊断输入 = st.session_state.custom_diagnosis_input.strip()

            # 在诊断目录中查找诊断编码
            诊断编码_原始 = find_diagnosis_code(诊断输入)

            if 诊断编码_原始:
                # 截取诊断编码到小数点后第一位
                诊断编码_传统 = truncate_diagnosis_code(诊断编码_原始)
                诊断名称_传统 = 诊断输入
                入组情况_诊断 = f"手动输入诊断: {诊断输入} -> 编码: {诊断编码_原始} -> 截断后: {诊断编码_传统}"
            else:
                # 如果没有找到诊断编码，尝试将输入作为编码处理
                诊断编码_传统 = truncate_diagnosis_code(诊断输入)
                诊断名称_传统 = 诊断输入
                入组情况_诊断 = f"手动输入诊断: {诊断输入} -> 直接作为编码处理 -> 截断后: {诊断编码_传统}"
        elif st.session_state.selected_diagnosis and st.session_state.selected_diagnosis != "手动输入诊断...":
            # 正常选择诊断模式
            诊断编码_传统 = st.session_state.selected_diagnosis.split(" - ")[
                0] if " - " in st.session_state.selected_diagnosis else st.session_state.selected_diagnosis
            诊断名称_传统 = st.session_state.selected_diagnosis.split(" - ")[
                1] if " - " in st.session_state.selected_diagnosis else st.session_state.selected_diagnosis
            if 诊断编码_传统 == "无":
                诊断编码_传统 = ""
            入组情况_诊断 = "正常选择诊断"
        else:
            诊断编码_传统 = ""
            诊断名称_传统 = "无"
            入组情况_诊断 = "未选择诊断"

    else:  # 先操作后诊断
        if st.session_state.selected_diagnosis == "手动输入诊断..." and st.session_state.custom_diagnosis_input:
            # 手动输入诊断模式
            诊断输入 = st.session_state.custom_diagnosis_input.strip()

            # 在诊断目录中查找诊断编码
            诊断编码_原始 = find_diagnosis_code(诊断输入)

            if 诊断编码_原始:
                # 截取诊断编码到小数点后第一位
                诊断编码_传统 = truncate_diagnosis_code(诊断编码_原始)
                诊断名称_传统 = 诊断输入
                入组情况_诊断 = f"手动输入诊断: {诊断输入} -> 编码: {诊断编码_原始} -> 截断后: {诊断编码_传统}"
            else:
                # 如果没有找到诊断编码，尝试将输入作为编码处理
                诊断编码_传统 = truncate_diagnosis_code(诊断输入)
                诊断名称_传统 = 诊断输入
                入组情况_诊断 = f"手动输入诊断: {诊断输入} -> 直接作为编码处理 -> 截断后: {诊断编码_传统}"
        elif st.session_state.selected_diagnosis and st.session_state.selected_diagnosis != "手动输入诊断...":
            # 正常选择诊断模式
            诊断编码_传统 = st.session_state.selected_diagnosis.split(" - ")[
                0] if " - " in st.session_state.selected_diagnosis else st.session_state.selected_diagnosis
            诊断名称_传统 = st.session_state.selected_diagnosis.split(" - ")[
                1] if " - " in st.session_state.selected_diagnosis else st.session_state.selected_diagnosis
            if 诊断编码_传统 == "无":
                诊断编码_传统 = ""
            入组情况_诊断 = "正常选择诊断"
        else:
            诊断编码_传统 = ""
            诊断名称_传统 = "无"
            入组情况_诊断 = "未选择诊断"

    # 处理操作信息
    if 查询顺序 == "先诊断后操作":
        if st.session_state.selected_operation == "手动输入操作...":
            # 手动输入操作模式
            if st.session_state.custom_operation_input:
                # 用户输入的内容作为操作编码或操作名称
                操作输入 = st.session_state.custom_operation_input.strip()

                # 获取诊断的病种类型
                诊断病种类型 = get_diagnosis_type(诊断编码_传统)

                # 情况1：在DIP目录库中查找匹配的操作
                匹配记录 = find_matching_operation(诊断编码_传统, 操作输入)

                if 匹配记录 is not None:
                    # 情况1：在DIP目录库中找到匹配记录
                    操作编码_传统 = 匹配记录['操作编码']
                    操作名称_传统 = 匹配记录['操作名称']
                    入组情况_操作 = "情况1：在DIP目录库中直接匹配入组"
                elif 诊断病种类型 == "综合病种":
                    # 情况2：诊断是综合病种，查找操作类别
                    操作类别 = find_operation_category(操作输入)

                    if 操作类别:
                        # 根据操作类别获取综合病种的DIP信息
                        综合病种记录 = get_comprehensive_dip_info(诊断编码_传统, 操作类别)

                        if 综合病种记录 is not None:
                            # 情况2：成功匹配综合病种
                            操作编码_传统 = 操作输入
                            操作名称_传统 = 操作输入
                            匹配记录 = 综合病种记录
                            入组情况_操作 = f"情况2：综合病种匹配，操作类别为{操作类别}"
                        else:
                            # 未找到匹配的综合病种记录
                            操作编码_传统 = 操作输入
                            操作名称_传统 = 操作输入
                            匹配记录 = None
                            入组情况_操作 = "无法入组：未找到匹配的综合病种记录"
                    else:
                        # 未找到操作类别
                        操作编码_传统 = 操作输入
                        操作名称_传统 = 操作输入
                        匹配记录 = None
                        入组情况_操作 = "无法入组：未找到操作类别"
                elif 诊断病种类型 in ["基层病种", "核心病种"] and (not 操作输入 or 操作输入 == "无"):
                    # 情况3：基层病种或核心病种，操作为空
                    无操作记录 = get_diagnosis_only_dip_info(诊断编码_传统)

                    if 无操作记录 is not None:
                        # 情况3：成功匹配无操作的病种
                        操作编码_传统 = "无"
                        操作名称_传统 = "无"
                        匹配记录 = 无操作记录
                        入组情况_操作 = f"情况3：{诊断病种类型}，无操作直接入组"
                    else:
                        # 未找到无操作的病种记录
                        操作编码_传统 = "无"
                        操作名称_传统 = "无"
                        匹配记录 = None
                        入组情况_操作 = f"无法入组：未找到{诊断病种类型}的无操作记录"
                else:
                    # 其他情况：无法入组
                    操作编码_传统 = 操作输入
                    操作名称_传统 = 操作输入
                    匹配记录 = None
                    入组情况_操作 = "无法入组：不满足入组条件"
            else:
                # 用户未输入操作
                操作编码_传统 = "无"
                操作名称_传统 = "无"
                匹配记录 = None
                入组情况_操作 = "未输入操作"
        elif st.session_state.selected_operation == "无操作的":
            # 用户选择了"无操作的"选项
            操作编码_传统 = "无"
            操作名称_传统 = "无"

            # 获取诊断的病种类型
            诊断病种类型 = get_diagnosis_type(诊断编码_传统)

            if 诊断病种类型 in ["基层病种", "核心病种"]:
                # 情况3：基层病种或核心病种，操作为空
                无操作记录 = get_diagnosis_only_dip_info(诊断编码_传统)

                if 无操作记录 is not None:
                    # 情况3：成功匹配无操作的病种
                    匹配记录 = 无操作记录
                    入组情况_操作 = f"情况3：{诊断病种类型}，无操作直接入组"
                else:
                    # 未找到无操作的病种记录
                    匹配记录 = None
                    入组情况_操作 = f"无法入组：未找到{诊断病种类型}的无操作记录"
            else:
                # 综合病种不能无操作
                匹配记录 = None
                入组情况_操作 = "无法入组：综合病种必须有操作"
        else:
            # 正常选择操作模式
            if st.session_state.selected_operation and st.session_state.selected_operation != "手动输入操作..." and st.session_state.selected_operation != "无操作的":
                操作编码_传统 = st.session_state.selected_operation.split(" - ")[
                    0] if " - " in st.session_state.selected_operation else st.session_state.selected_operation
                操作名称_传统 = st.session_state.selected_operation.split(" - ")[
                    1] if " - " in st.session_state.selected_operation else "无"

                # 在DIP目录库中查找匹配记录
                匹配记录 = find_matching_operation(诊断编码_传统, 操作编码_传统)
                入组情况_操作 = "正常选择：在DIP目录库中匹配"
            else:
                操作编码_传统 = "无"
                操作名称_传统 = "无"
                匹配记录 = None
                入组情况_操作 = "未选择操作"
    else:  # 先操作后诊断
        if st.session_state.selected_operation == "手动输入操作...":
            # 手动输入操作模式
            if st.session_state.custom_operation_input:
                # 用户输入的内容作为操作编码或操作名称
                操作输入 = st.session_state.custom_operation_input.strip()

                # 获取诊断的病种类型
                诊断病种类型 = get_diagnosis_type(诊断编码_传统)

                # 情况1：在DIP目录库中查找匹配的操作
                匹配记录 = find_matching_operation(诊断编码_传统, 操作输入)

                if 匹配记录 is not None:
                    # 情况1：在DIP目录库中找到匹配记录
                    操作编码_传统 = 匹配记录['操作编码']
                    操作名称_传统 = 匹配记录['操作名称']
                    入组情况_操作 = "情况1：在DIP目录库中直接匹配入组"
                elif 诊断病种类型 == "综合病种":
                    # 情况2：诊断是综合病种，查找操作类别
                    操作类别 = find_operation_category(操作输入)

                    if 操作类别:
                        # 根据操作类别获取综合病种的DIP信息
                        综合病种记录 = get_comprehensive_dip_info(诊断编码_传统, 操作类别)

                        if 综合病种记录 is not None:
                            # 情况2：成功匹配综合病种
                            操作编码_传统 = 操作输入
                            操作名称_传统 = 操作输入
                            匹配记录 = 综合病种记录
                            入组情况_操作 = f"情况2：综合病种匹配，操作类别为{操作类别}"
                        else:
                            # 未找到匹配的综合病种记录
                            操作编码_传统 = 操作输入
                            操作名称_传统 = 操作输入
                            匹配记录 = None
                            入组情况_操作 = "无法入组：未找到匹配的综合病种记录"
                    else:
                        # 未找到操作类别
                        操作编码_传统 = 操作输入
                        操作名称_传统 = 操作输入
                        匹配记录 = None
                        入组情况_操作 = "无法入组：未找到操作类别"
                elif 诊断病种类型 in ["基层病种", "核心病种"] and (not 操作输入 or 操作输入 == "无"):
                    # 情况3：基层病种或核心病种，操作为空
                    无操作记录 = get_diagnosis_only_dip_info(诊断编码_传统)

                    if 无操作记录 is not None:
                        # 情况3：成功匹配无操作的病种
                        操作编码_传统 = "无"
                        操作名称_传统 = "无"
                        匹配记录 = 无操作记录
                        入组情况_操作 = f"情况3：{诊断病种类型}，无操作直接入组"
                    else:
                        # 未找到无操作的病种记录
                        操作编码_传统 = "无"
                        操作名称_传统 = "无"
                        匹配记录 = None
                        入组情况_操作 = f"无法入组：未找到{诊断病种类型}的无操作记录"
                else:
                    # 其他情况：无法入组
                    操作编码_传统 = 操作输入
                    操作名称_传统 = 操作输入
                    匹配记录 = None
                    入组情况_操作 = "无法入组：不满足入组条件"
            else:
                # 用户未输入操作
                操作编码_传统 = "无"
                操作名称_传统 = "无"
                匹配记录 = None
                入组情况_操作 = "未输入操作"
        elif st.session_state.selected_operation == "无操作的":
            # 用户选择了"无操作的"选项
            操作编码_传统 = "无"
            操作名称_传统 = "无"

            # 获取诊断的病种类型
            诊断病种类型 = get_diagnosis_type(诊断编码_传统)

            if 诊断病种类型 in ["基层病种", "核心病种"]:
                # 情况3：基层病种或核心病种，操作为空
                无操作记录 = get_diagnosis_only_dip_info(诊断编码_传统)

                if 无操作记录 is not None:
                    # 情况3：成功匹配无操作的病种
                    匹配记录 = 无操作记录
                    入组情况_操作 = f"情况3：{诊断病种类型}，无操作直接入组"
                else:
                    # 未找到无操作的病种记录
                    匹配记录 = None
                    入组情况_操作 = f"无法入组：未找到{诊断病种类型}的无操作记录"
            else:
                # 综合病种不能无操作
                匹配记录 = None
                入组情况_操作 = "无法入组：综合病种必须有操作"
        else:
            # 正常选择操作模式
            if st.session_state.selected_operation and st.session_state.selected_operation != "手动输入操作..." and st.session_state.selected_operation != "无操作的":
                操作编码_传统 = st.session_state.selected_operation.split(" - ")[
                    0] if " - " in st.session_state.selected_operation else st.session_state.selected_operation
                操作名称_传统 = st.session_state.selected_operation.split(" - ")[
                    1] if " - " in st.session_state.selected_operation else "无"

                # 在DIP目录库中查找匹配记录
                匹配记录 = find_matching_operation(诊断编码_传统, 操作编码_传统)
                入组情况_操作 = "正常选择：在DIP目录库中匹配"
            else:
                操作编码_传统 = "无"
                操作名称_传统 = "无"
                匹配记录 = None
                入组情况_操作 = "未选择操作"

    if 操作编码_传统 == "无":
        操作编码_传统 = ""

    # 如果没有匹配记录，尝试在DIP数据库中查找匹配的诊断记录
    if 匹配记录 is None and 诊断编码_传统:
        匹配记录 = find_matching_diagnosis(诊断编码_传统)
        if 匹配记录 is not None:
            入组情况_诊断 = f"手动输入诊断匹配成功: {诊断编码_传统}"

    # 获取完整的记录信息
    if 匹配记录 is not None:
        # 找到匹配记录
        诊断名称_传统 = replace_nan_with_chinese(匹配记录['诊断名称'])
        诊断编码_传统 = 诊断编码_传统
        操作名称_传统 = replace_nan_with_chinese(匹配记录['操作名称']) if '操作名称' in 匹配记录 else 操作名称_传统
        操作编码_传统 = 操作编码_传统 if 操作编码_传统 else replace_nan_with_chinese(匹配记录.get('操作编码', '无'))
        入组的DIP基准分值_传统 = 匹配记录['入组的DIP基准分值']
        # 同步更新session state中的基准分值
        st.session_state.dip_base_score = 入组的DIP基准分值_传统
        DIP编码_传统 = replace_nan_with_chinese(匹配记录.get('DIP编码', '无'))
        DIP名称_传统 = replace_nan_with_chinese(匹配记录.get('DIP名称', '无'))
        病种类型_传统 = replace_nan_with_chinese(匹配记录.get('病种类型', '无'))
        可入组 = True
    else:
        # 未找到匹配记录
        诊断名称_传统 = 诊断名称_传统 if '诊断名称_传统' in locals() else "无"
        诊断编码_传统 = 诊断编码_传统
        操作名称_传统 = 操作名称_传统 if '操作名称_传统' in locals() else "无"
        操作编码_传统 = 操作编码_传统
        入组的DIP基准分值_传统 = 27.7173  # 使用图片中的默认值
        # 同步更新session state中的基准分值
        st.session_state.dip_base_score = 入组的DIP基准分值_传统
        DIP编码_传统 = "无"
        DIP名称_传统 = "无法入组"
        病种类型_传统 = "无法入组"
        可入组 = False

    # 更新全局变量
    诊断名称 = 诊断名称_传统
    诊断编码 = 诊断编码_传统
    操作名称 = 操作名称_传统
    操作编码 = 操作编码_传统
    入组的DIP基准分值 = 入组的DIP基准分值_传统
    DIP编码 = DIP编码_传统
    DIP名称 = DIP名称_传统
    病种类型 = 病种类型_传统

    # 更新滑块和输入框的session state值
    st.session_state['dip_base_score_input'] = 入组的DIP基准分值_传统
    st.session_state['dip_base_score_slider'] = 入组的DIP基准分值_传统

    # 显示入组情况
    with st.sidebar.expander("📋 入组情况", expanded=True):
        st.write(f"**查询顺序:** {查询顺序}")
        st.write(
            f"**诊断模式:** {'手动输入' if st.session_state.selected_diagnosis == '手动输入诊断...' else '目录选择'}")
        st.write(
            f"**操作模式:** {'手动输入' if st.session_state.selected_operation == '手动输入操作...' else '目录选择'}")
        st.write(f"**诊断入组情况:** {入组情况_诊断}")
        if '入组情况_操作' in locals():
            st.write(f"**操作入组情况:** {入组情况_操作}")
        st.write(f"**DIP编码:** {DIP编码}")
        st.write(f"**DIP名称:** {DIP名称}")
        st.write(f"**病种类型:** {病种类型}")
        st.write(f"**诊断编码:** {诊断编码}")
        st.write(f"**诊断名称:** {诊断名称}")
        st.write(f"**操作编码:** {操作编码}")
        st.write(f"**操作名称:** {操作名称}")

# 添加入组的DIP基准分值输入框
# 使用session state来存储和同步分值
if 'dip_base_score' not in st.session_state:
    st.session_state.dip_base_score = 27.7173

# 输入框
入组的DIP基准分值 = st.sidebar.number_input(
    '入组的DIP基准分值',
    min_value=0.0,
    max_value=5000.0,
    value=st.session_state.dip_base_score,  # 使用session state中的值
    step=0.0001,
    format="%.4f",
    key='dip_base_score_input'  # 添加key
)
# 滑块
入组的DIP基准分值_slider = st.sidebar.slider(
    '入组的DIP基准分值(滑块)',
    0.0, 5000.0,
    float(st.session_state.dip_base_score),  # 使用session state中的值
    50.0,
    key='dip_base_score_slider'  # 添加key
)

# 确保输入框和滑块的值同步
if 入组的DIP基准分值 != st.session_state.dip_base_score:
    st.session_state.dip_base_score = 入组的DIP基准分值
if 入组的DIP基准分值_slider != st.session_state.dip_base_score:
    st.session_state.dip_base_score = 入组的DIP基准分值_slider

# 计算入组的DIP分值
入组的DIP分值 = 入组的DIP基准分值 * 医院等级系数

# 显示计算得到的入组的DIP分值
st.sidebar.info(f"计算得到的入组的DIP分值: **{入组的DIP分值:.4f}**")

# 计算指标
results = calculate_dip_metrics(
    诊疗费用, 检查检验费用, 药品费用, 耗材费用,
    医疗性收入成本率, 药耗成本率, 统筹基金支付金额,
    入组的DIP基准分值, 医院等级系数, 点值
)

# 显示结果
st.header('分析结果')

# 关键指标卡片
col1, col2, col3 = st.columns(3)

with col1:
    # 盈亏金额显示
    盈亏颜色 = 'green' if results['病例真实盈亏金额'] >= 0 else 'red'
    st.metric(
        label="病例真实盈亏金额",
        value=f"¥{results['病例真实盈亏金额']:,.2f}",
        delta_color="off"
    )

with col2:
    # 回款率显示
    回款率颜色 = 'green' if results['DIP回款率'] >= 1.0 else 'red'
    st.metric(
        label="DIP回款率",
        value=f"{results['DIP回款率']:.2%}",
        delta_color="off"
    )

with col3:
    # DIP盈亏金额显示
    DIP盈亏颜色 = 'green' if results['DIP盈亏金额'] >= 0 else 'red'
    st.metric(
        label="DIP盈亏金额",
        value=f"¥{results['DIP盈亏金额']:,.2f}",
        delta_color="off"
    )

# 可视化图表
fig = make_subplots(
    rows=1, cols=2,
    subplot_titles=('费用结构分析', '盈亏分析'),
    specs=[[{"type": "pie"}, {"type": "bar"}]]
)

# 饼图：费用结构
费用分类 = ['诊疗费用', '检查检验费用', '药品费用', '耗材费用']
费用数值 = [诊疗费用, 检查检验费用, 药品费用, 耗材费用]

fig.add_trace(
    go.Pie(labels=费用分类, values=费用数值, name="费用结构"),
    row=1, col=1
)

# 柱状图：盈亏分析
DIP盈亏金额 = results['DIP盈亏金额']
真实盈亏金额 = results['病例真实盈亏金额']

fig.add_trace(
    go.Bar(x=['DIP盈亏金额', '真实盈亏金额'],
           y=[DIP盈亏金额, 真实盈亏金额],
           name="金额指标",
           marker_color=['blue', 'green']),
    row=1, col=2
)

# 添加第二个Y轴用于显示百分比
fig.update_layout(
    xaxis2=dict(title="指标"),
    yaxis2=dict(title="金额", side="left"),
    yaxis3=dict(title="回款率 (%)",
                side="right",
                overlaying="y2",
                range=[0, max(100, results['DIP回款率'] * 100 + 10)],
                showgrid=False)
)

# 添加回款率线图（在右侧Y轴）
fig.add_trace(
    go.Scatter(x=['DIP回款率'],
               y=[results['DIP回款率'] * 100],
               mode='markers+text',
               marker=dict(size=15, color='red'),
               text=[f"{results['DIP回款率'] * 100:.1f}%"],
               textposition="middle right",
               name="DIP回款率",
               yaxis="y3"),
    row=1, col=2
)

fig.update_layout(
    height=400,
    showlegend=True,
    title_text="DIP病种及费用分析"
)

st.plotly_chart(fig, use_container_width=True)

# 显示当前选择的DIP信息
st.header('当前选择的DIP病种信息')
col1, col2 = st.columns(2)

with col1:
    st.info(f"""
    **诊断信息:**
    - 诊断编码: {诊断编码}
    - 诊断名称: {诊断名称}

    **操作信息:**
    - 操作编码: {操作编码}
    - 操作名称: {操作名称}
    """)

with col2:
    st.info(f"""
    **DIP信息:**
    - DIP编码: {DIP编码}
    - DIP名称: {DIP名称}
    - 病种类型: {病种类型}
    - 基准分值: {入组的DIP基准分值:.4f}
    - 计算分值: {入组的DIP分值:.4f}
    """)

# 显示DIP数据库
st.header('当前DIP病种及分值目录库')
# 在显示前处理数据库中的NaN值
display_database = st.session_state.dip_database.copy()
for col in display_database.columns:
    if display_database[col].dtype == 'object':
        display_database[col] = display_database[col].apply(replace_nan_with_chinese)
st.dataframe(display_database)

# 显示手术操作分类目录
st.header('当前手术操作分类目录')
# 在显示前处理数据库中的NaN值
display_surgery_database = st.session_state.surgery_database.copy()
for col in display_surgery_database.columns:
    if display_surgery_database[col].dtype == 'object':
        display_surgery_database[col] = display_surgery_database[col].apply(replace_nan_with_chinese)
st.dataframe(display_surgery_database)

# 显示诊断编码及名称目录
st.header('当前诊断编码及名称目录')
# 在显示前处理数据库中的NaN值
display_diagnosis_database = st.session_state.diagnosis_database.copy()
for col in display_diagnosis_database.columns:
    if display_diagnosis_database[col].dtype == 'object':
        display_diagnosis_database[col] = display_diagnosis_database[col].apply(replace_nan_with_chinese)
st.dataframe(display_diagnosis_database)

# 详细计算数据表格
st.header('详细计算数据')
detail_data = {
    '指标': ['住院总费用', '医疗性收入', '药耗收入', '治疗成本', '病人自付金额',
             'DIP支付标准', 'DIP核算金额', 'DIP盈亏金额', '病例真实盈亏金额', 'DIP回款率', '入组的DIP分值'],
    '数值': [
        results['住院总费用'],
        诊疗费用 + 检查检验费用,
        药品费用 + 耗材费用,
        results['治疗成本'],
        results['住院总费用'] - 统筹基金支付金额,
        results['DIP支付标准'],
        results['DIP核算金额'],
        results['DIP盈亏金额'],
        results['病例真实盈亏金额'],
        results['DIP回款率'],
        results['入组的DIP分值']
    ]
}
df = pd.DataFrame(detail_data)


# 格式化显示
def format_value(x, is_percentage=False):
    if is_percentage:
        return f"{x:.2%}"
    elif isinstance(x, (int, float)):
        return f"¥{x:,.2f}"
    else:
        return str(x)


df['数值'] = df.apply(lambda row:
                      format_value(row['数值'], is_percentage=(row['指标'] == 'DIP回款率')),
                      axis=1
                      )

st.table(df)

# 添加当前参数值显示
st.sidebar.header('当前参数值')
st.sidebar.write(f"诊疗费用: {诊疗费用:.2f}")
st.sidebar.write(f"检查检验费用: {检查检验费用:.2f}")
st.sidebar.write(f"药品费用: {药品费用:.2f}")
st.sidebar.write(f"耗材费用: {耗材费用:.2f}")
st.sidebar.write(f"医疗性收入成本率: {医疗性收入成本率:.2f}")
st.sidebar.write(f"药耗成本率: {药耗成本率:.2f}")
st.sidebar.write(f"统筹基金支付金额: {统筹基金支付金额:.2f}")
st.sidebar.write(f"入组的DIP基准分值: {入组的DIP基准分值:.4f}")
st.sidebar.write(f"医院等级系数: {医院等级系数:.4f}")
st.sidebar.write(f"计算得到的入组的DIP分值: {入组的DIP分值:.4f}")
st.sidebar.write(f"点值类型: {点值类型}")
st.sidebar.write(f"点值: {点值:.4f}")