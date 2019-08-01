from table import Table
from bitstream import BitStream
import math

def more_rbsp_data(bs: BitStream):
    n = bs.available()
    if n > 8:
        return True
    elif n <= 0:
        return False

    b = bs.read_bits(n, forward=False)
    return not b == (1 << (n-1))


def find_start_code(bs: BitStream):
    start_code_len = 0
    try:
        while True:
            head = bs.read_bytes_to_array(4)
            pos = bs.pos()

            if head[0] == 0 and head[1] == 0 and head[2] == 1:
                bs.moveto(pos.byte-1, pos.bit)
                start_code_len = 3
                break
            elif head[0] == 0 and head[1] == 0 and head[2] == 0 and head[3] == 1:
                start_code_len = 4
                break
            else:
                bs.moveto(pos.byte-3, pos.bit)
    except EOFError as e:
        return 0
    return start_code_len


def rbsp_data(bs: BitStream):
    from_byte = bs.pos().byte
    n = find_start_code(bs)
    to_byte = bs.pos().byte

    num = to_byte - from_byte - n

    bs.moveto(from_byte, 0)

    rbsp = bytearray()
    i = 0
    while i < num:
        if i <= num - 3:
            next_3_byte = bs.read_bytes_to_array(3, forward=False)
            if next_3_byte[0] == 0 and next_3_byte[1] == 0 and next_3_byte[2] == 3:
                rbsp.extend([0, 0])
                bs.skip(3, 0)
                i += 3
                continue

        rbsp.extend(bs.read_bytes_to_array(1))
        i += 1

    return rbsp

def __read_topleft_bottomright(d, bs):
    d.top_left = []
    d.bottom_right = []
    for i in range(d.num_slice_groups_minus1+1):
        d.top_left.append(bs.read_ue_golomb())
        d.bottom_right.append(bs.read_ue_golomb())

def pic_parameter_set_rbsp(d:Table, bs:BitStream):
    d.add_field('pic_parameter_set_id', bs.read_ue_golomb)
    d.add_field('seq_parameter_set_id', bs.read_ue_golomb)
    d.add_field('entropy_coding_mode_flag', bs.read_a_bit)
    d.add_field('bottom_field_pic_order_in_frame_present_flag', bs.read_a_bit)
    d.add_field('num_slice_groups_minus1', bs.read_ue_golomb)
    if d.num_slice_groups_minus1 > 0:
        d.add_field('slice_group_map_type', bs.read_ue_golomb)
        if d.slice_group_map_type == 0:
            d.add_field('run_length_minus1', bs.read_ue_golombs, count=(d.num_slice_groups_minus1+1))
        elif d.slice_group_map_type == 2:
            d.add_fields(__read_topleft_bottomright, 'top_left', 'bottom_right')
        elif d.slice_group_map_type in [3,4,5]:
            d.add_field('slice_group_change_direction_flag', bs.read_a_bit)
            d.add_field('slice_group_change_rate_minus', bs.read_ue_golomb)
        elif d.slice_group_map_type == 6:
            d.add_field('pic_size_in_map_units_minus1', bs.read_ue_golomb)
            d.add_field('slice_group_id', bs.readbitss, count=math.ceil(math.log2(d.num_slice_groups_minus1+1)), times=(pic_size_in_map_units_minus1+1))
    d.add_field('num_ref_idx_l0_default_active_minus1', bs.read_ue_golomb)
    d.add_field('num_ref_idx_l1_default_active_minus1', bs.read_ue_golomb)
    d.add_field('weighted_pred_flag', bs.read_a_bit)
    d.add_field('weighted_bipred_idc', bs.read_bits, count=2)
    d.add_field('pic_init_qp_minus26', bs.read_se_golomb)
    d.add_field('pic_init_qs_minus26', bs.read_se_golomb)
    d.add_field('chroma_qp_index_offset', bs.read_se_golomb)
    d.add_field('deblocking_filter_control_present_flag', bs.read_a_bit)
    d.add_field('constrained_intra_pred_flag', bs.read_a_bit)
    d.add_field('redundant_pic_cnt_present_flag', bs.read_a_bit)
    if more_rbsp_data(bs):
        d.add_field('transform_8x8_mode_flag', bs.read_a_bit)
        d.add_field('pic_scaling_matrix_present_flag', bs.read_a_bit)
        if d.pic_scaling_matrix_present_flag:
            d.add_fields(__pps_fields_in_scaling_list, 'pps_scaling_list_present_flag', 'ScalingList4x4',
                         'UseDefaultScalingMatrix4x4Flag', 'ScalingList8x8', 'UseDefaultScalingMatrix8x8Flag')
        d.add_field('second_chroma_qp_index_offset', bs.read_se_golomb)
    rbsp_trailing_bits(d, bs)


def nal_unit_header_svc_extension(d:Table, bs:BitStream):
    d.add_field('idr_flag priority_id', bs.read_bits, count=1)
    d.add_field('no_inter_layer_pred_flag', bs.read_bits, count=6)
    d.add_field('dependency_id', bs.read_bits, count=1)
    d.add_field('quality_id', bs.read_bits, count=3)
    d.add_field('temporal_id', bs.read_bits, count=4)
    d.add_field('use_ref_base_pic_flag', bs.read_bits, count=1)
    d.add_field('discardable_flag', bs.read_bits, count=1)
    d.add_field('output_flag', bs.read_bits, count=1)
    d.add_field('reserved_three_2bits', bs.read_bits, count=5)

def nal_unit_header_3davc_extension(d:Table, bs:BitStream):
    d.add_field('view_idx', bs.read_bits, count=8)
    d.add_field('depth_flag', bs.read_bits, count=1)
    d.add_field('non_idr_flag', bs.read_bits, count=1)
    d.add_field('temporal_id', bs.read_bits, count=3)
    d.add_field('anchor_pic_flag', bs.read_bits, count=1)
    d.add_field('inter_view_flag', bs.read_bits, count=1)

def nal_unit_header_mvc_extension(d:Table, bs:BitStream):
    d.add_field('non_idr_flag', bs.read_bits, count=1)
    d.add_field('priority_id', bs.read_bits, count=6)
    d.add_field('view_id', bs.read_bits, count=10)
    d.add_field('temporal_id', bs.read_bits, count=3)
    d.add_field('anchor_pic_flag', bs.read_bits, count=1)
    d.add_field('inter_view_flag', bs.read_bits, count=1)
    d.add_field('reserved_one_bit', bs.read_bits, count=1)

def nal_unit(d:Table, bs:BitStream):
    d.add_field('forbidden_zero_bit', bs.read_bits,
                count=1)
    d.add_field('nal_ref_idc', bs.read_bits, count=2)
    d.add_field('nal_unit_type', bs.read_bits, count=5)
    if d.nal_unit_type in [14,20,21]:
        if not d.nal_unit_type == 21:
            d.add_field('svc_extension_flag', bs.read_a_bit)
        else:
            d.add_field('avc_extension_flag', bs.read_a_bit)
        if d.svc_extension_flag:
            d.add_table(nal_unit_header_svc_extension)
            pass
        elif d.get_value('avc_extension_flag',0):
            d.add_table(nal_unit_header_3davc_extension)
            pass
        else:
            d.add_table(nal_unit_header_mvc_extension)
            pass
    d.add_field('rbsp', rbsp_data, bs=bs)


def rbsp_trailing_bits(d:Table, bs:BitStream):
    d.add_field('rbsp_stop_one_bit', bs.read_bits, count=1)
    bs.to_byte_end()


def access_unit_delimiter_rbsp(d:Table, bs:BitStream):
    d.add_field('primary_picture_type', bs.read_bits, count=3)
    rbsp_trailing_bits(d,bs)


def sei_ff_coding(bs: BitStream):
    value = 0
    next_byte = 0xFF
    while next_byte == 0xFF:
        next_byte = bs.read_bits(8)
        value += next_byte
    return value


def sei_message(d:Table, bs:BitStream):
    d.add_field('payload_type', sei_ff_coding, bs=bs)
    d.add_field('payload_size', sei_ff_coding, bs=bs)
    d.add_field('sei_payload', bs.read_bytes_to_array, count=d.payload_size)


def sei_rbsp(d:Table, bs:BitStream):
    while more_rbsp_data(bs):
        d.add_table(sei_message)
    rbsp_trailing_bits(d,bs)


def __find_pps_in_ctx(id, ctx:Table):
    for f in ctx.fields:
        if f.name == 'pic_parameter_set_rbsp':
            if f.pic_parameter_set_id == id:
                return f
    return None

def __find_sps_in_ctx(id, ctx:Table):
    for f in ctx.fields:
        if f.name == 'seq_parameter_set_rbsp' or f.name == 'subset_seq_parameter_set_rbsp':
            if f.seq_parameter_set_data.seq_parameter_set_id == id:
                return f.seq_parameter_set_data
    return None

def __read_delta_pic_order_cnt(sps, pps, d, bs):
    ret = []
    if sps.pic_order_cnt_type == 1 and not sps.delta_pic_order_always_zero_flag:
        ret.append(bs.read_se_golomb)
        if pps.bottom_field_pic_order_in_frame_present_flag and not d.get_value('field_pic_flag', 0):
            ret.append(bs.read_se_golomb)
    return ret

def ref_pic_list_mvc_modification(d:Table, bs:BitStream):
    pass

def __read_ref_pic_list(d:Table, bs:BitStream):
    d.modification_of_pic_num_idc = []
    d.abs_diff_pic_num_minus1 = []
    d.long_term_pic_num = []
    while True:
        d.modification_of_pic_num_idc.append(bs.read_se_golomb())
        if d.modification_of_pic_num_idc[-1] in [0,1]:
            d.abs_diff_pic_num_minus1.append(bs.read_se_golomb())
        elif d.modification_of_pic_num_idc[-1] == 2:
            d.long_term_pic_num.append(bs.read_se_golomb())
        elif d.modification_of_pic_num_idc[-1] == 3:
            break

def ref_pic_list_modification(d:Table, bs:BitStream, type):
    if type in [2,4]: #I SI
        d.add_field('ref_pic_list_modification_flag_l0', bs.read_a_bit)
        if d.ref_pic_list_modification_flag_l0:
            d.add_fields(__read_ref_pic_list, 'modification_of_pic_num_idc', 'abs_diff_pic_num_minus1', 'long_term_pic_num')
    elif type == 1: #B
        d.add_field('ref_pic_list_modification_flag_l1', bs.read_a_bit)
        if d.ref_pic_list_modification_flag_l1:
            d.add_fields(__read_ref_pic_list, 'modification_of_pic_num_idc', 'abs_diff_pic_num_minus1', 'long_term_pic_num')


def slice_header(d:Table, bs:BitStream):
    d.add_field('first_mb_in_slice', bs.read_ue_golomb)
    d.add_field('slice_type', bs.read_ue_golomb)
    d.add_field('pic_parameter_set_id', bs.read_ue_golomb)
    pps = __find_pps_in_ctx(d.pic_parameter_set_id, d.context)
    if pps == None:
        raise Exception('no pps in ctx, abort!')
    sps = __find_sps_in_ctx(pps.seq_parameter_set_id, d.context)
    if pps == None:
        raise Exception('no sps in ctx, abort!')
    if sps.get_value('separate_colour_plane_flag', 0):
        d.add_field('colour_plane_id', bs.read_bits, count=2)
    try:
        nal_unit = d.context.nal_unit
    except AttributeError as e:
        raise Exception('no nal_unit in ctx, abort!')
    
    d.add_field('frame_num', bs.read_bits, count = (sps.log2_max_frame_num_minus4 + 4))
    if not sps.frame_mbs_only_flag:
        d.add_field('field_pic_flag', bs.read_a_bit)
        if d.field_pic_flag:
            d.add_field('bottom_field_flag', bs.read_a_bit)
    
    if nal_unit.nal_unit_type == 5: #IdrPicFlag
        d.add_field('idr_pic_id',  bs.read_ue_golomb)
    
    if sps.pic_order_cnt_type == 0:
        d.add_field('pic_order_cnt_lsb', bs.read_bits, count=(sps.log2_max_pic_order_cnt_lsb_minus4+4))
        if pps.bottom_field_pic_order_in_frame_present_flag and not d.get_value('field_pic_flag', 0):
            bs.add_field('delta_pic_order_cnt_bottom', bs.read_se_golomb)
    
    d.add_field('delta_pic_order_cnt', __read_delta_pic_order_cnt, sps=sps, pps=pps, d=d, bs=bs)
    if pps.redundant_pic_cnt_present_flag:
        d.add_field('redundant_pic_cnt', bs.read_ue_golomb)
    
    slice_type = d.slice_type % 5
    if slice_type == 1: #B
        d.add_field('direct_spatial_mv_pred_flag', bs.read_a_bit)
    if slice_type in [0,1,3]: #P SP B
        d.add_field('num_ref_idx_active_override_flag', bs.read_a_bit)
        if d.num_ref_idx_active_override_flag:
            d.add_field('num_ref_idx_l0_active_minus1', bs.read_ue_golomb)
        if slice_type == 1: #B
            d.add_field('num_ref_idx_l1_active_minus1', bs.read_ue_golomb)
    
    if nal_unit.nal_unit_type in [20,21]:
        d.add_table(ref_pic_list_mvc_modification, type=slice_type)
    else:
        d.add_table(ref_pic_list_modification, type=slice_type)



def slice_data(d:Table, bs:BitStream):
    pass


def slice_layer_without_partitioning_rbsp(d:Table, bs:BitStream):
    d.add_table(slice_header)
    d.add_table(slice_data)
    rbsp_trailing_bits(d,bs)


def slice_layer_extension_rbsp(d:Table, bs:BitStream):
    try:
        nal_unit = d.context.nal_unit
    except AttributeError as e:
        raise Exception('no nal_unit in ctx, abort!')
    if nal_unit.get_value('svc_extension_flag', 0):
        pass
    elif nal_unit.get_value('avc_3d_extension_flag', 0):
        pass
    else:
        d.add_table(slice_header)
        d.add_table(slice_data)
    rbsp_trailing_bits(d, bs)


def scaling_list(ScalingList, bs, UseDefaultScalingMatrix, i):
    last_scale = 8
    next_scale = 8
    size_of_scalinglist = len(ScalingList)

    for j in range(size_of_scalinglist):
        if next_scale != 0:
            delta_scale = bs.read_se_golomb()
            next_scale = (last_scale + delta_scale + 256) % 256
            UseDefaultScalingMatrix[i] = (j == 0 and next_scale == 0)
        ScalingList[j] = last_scale if next_scale == 0 else next_scale
        last_scale = ScalingList[j]


def __fields_by_cpb_cnt_minus1(d:Table, bs:BitStream):
    d.bit_rate_value_minus1 = [0]*(d.cpb_cnt_minus1+1)
    d.cpb_size_value_minus1 = [0]*(d.cpb_cnt_minus1+1)
    d.cbr_flag = [0]*(d.cpb_cnt_minus1+1)
    for i in range(d.cpb_cnt_minus1+1):
        d.bit_rate_value_minus1[i] = bs.read_ue_golomb()
        d.cpb_size_value_minus1[i] = bs.read_ue_golomb()
        d.cbr_flag[i] = bs.read_a_bit()


def hrd_parameters(d:Table, bs:BitStream):
    d.add_field('cpb_cnt_minus1', bs.read_ue_golomb)
    d.add_field('bit_rate_scale', bs.read_bits, count=4)
    d.add_field('cpb_size_scale', bs.read_bits, count=4)

    d.add_fields(__fields_by_cpb_cnt_minus1, 'bit_rate_value_minus1',
                 'cpb_size_value_minus1', 'cbr_flag')

    d.add_field('initial_cpb_removal_delay_length_minus1',
                bs.read_bits, count=5)
    d.add_field('cpb_removal_delay_length_minus1', bs.read_bits, count=5)
    d.add_field('dpb_output_delay_length_minus1', bs.read_bits, count=5)
    d.add_field('time_offset_length', bs.read_bits, count=5)


def vui_parameters(d:Table, bs:BitStream):
    d.add_field('aspect_ratio_info_present_flag', bs.read_a_bit)
    if d.aspect_ratio_info_present_flag:
        d.add_field('aspect_ratio_idc', bs.read_bits, count=8)
        if d.aspect_ratio_idc == 255:  # Extended_SAR
            d.add_field('sar_width', bs.read_bits, count=16)
            d.add_field('sar_height', bs.read_bits, count=16)
    d.add_field('overscan_info_present_flag', bs.read_a_bit)
    if d.overscan_info_present_flag:
        d.add_field('overscan_appropriate_flag', bs.read_a_bit)
    d.add_field('video_signal_type_present_flag', bs.read_a_bit)
    if d.video_signal_type_present_flag:
        d.add_field('video_format', bs.read_bits, count=3)
        d.add_field('video_full_range_flag', bs.read_a_bit)
        d.add_field('colour_description_present_flag', bs.read_a_bit)
        if d.colour_description_present_flag:
            d.add_field('colour_primaries', bs.read_bits, count=8)
            d.add_field('transfer_characteristics', bs.read_bits, count=8)
            d.add_field('matrix_coefficients', bs.read_bits, count=8)
    d.add_field('chroma_loc_info_present_flag', bs.read_a_bit)
    if d.chroma_loc_info_present_flag:
        d.add_field('chroma_sample_loc_type_top_field', bs.read_ue_golomb)
        d.add_field('chroma_sample_loc_type_bottom_field', bs.read_ue_golomb)
    d.add_field('timing_info_present_flag', bs.read_a_bit)
    if d.timing_info_present_flag:
        d.add_field('num_units_in_tick', bs.read_bits, count=32)
        d.add_field('timescale', bs.read_bits, count=32)
        d.add_field('fixed_frame_rate_flag', bs.read_a_bit)
    d.add_field('nal_hrd_parameters_present_flag', bs.read_a_bit)
    if d.nal_hrd_parameters_present_flag:
        d.add_table(hrd_parameters)
    d.add_field('vcl_hrd_parameters_present_flag', bs.read_a_bit)
    if d.vcl_hrd_parameters_present_flag:
        d.add_table(hrd_parameters)
    if d.nal_hrd_parameters_present_flag or d.vcl_hrd_parameters_present_flag:
        d.add_field('low_delay_hrd_flag', bs.read_a_bit)
    d.add_field('pic_struct_present_flag', bs.read_a_bit)
    d.add_field('bitstream_restriction_flag', bs.read_a_bit)
    if d.bitstream_restriction_flag:
        d.add_field('motion_vectors_over_pic_boundaries_flag', bs.read_a_bit)
        d.add_field('max_bytes_per_pic_denom', bs.read_ue_golomb)
        d.add_field('max_bits_per_mb_denom', bs.read_ue_golomb)
        d.add_field('log2_max_mv_length_horizontal', bs.read_ue_golomb)
        d.add_field('log2_max_mv_length_vertical', bs.read_ue_golomb)
        d.add_field('max_num_reorder_frames', bs.read_ue_golomb)
        d.add_field('max_dec_frame_buffering', bs.read_ue_golomb)


def __pps_fields_in_scaling_list(d:Table, bs:BitStream):
    sps = __find_sps_in_ctx(d.seq_parameter_set_id, d.context)
    num = 8 if sps.chroma_format_idc != 3 else 12
    d.pic_scaling_list_present_flag = [0]*num
    d.ScalingList4x4 = [[0]*16 for i in range(6)]
    d.UseDefaultScalingMatrix4x4Flag = [False]*6
    d.ScalingList8x8 = [[0]*64 for i in range(6)]
    d.UseDefaultScalingMatrix8x8Flag = [False]*6
    for i in range(num):
        d.pic_scaling_list_present_flag[i] = bs.read_bits(1)
        if d.pic_scaling_list_present_flag[i]:
            if i < 6:
                scaling_list(
                    d.ScalingList4x4[i], bs, d.UseDefaultScalingMatrix4x4Flag, i)
            else:
                scaling_list(
                    d.ScalingList8x8[i-6], bs, d.UseDefaultScalingMatrix8x8Flag, i-6)

def __fields_in_scaling_list(d:Table, bs:BitStream):
    num = 8 if d.chroma_format_idc != 3 else 12
    d.seq_scaling_list_present_flag = [0]*num
    d.ScalingList4x4 = [[0]*16 for i in range(6)]
    d.UseDefaultScalingMatrix4x4Flag = [False]*6
    d.ScalingList8x8 = [[0]*64 for i in range(6)]
    d.UseDefaultScalingMatrix8x8Flag = [False]*6
    for i in range(num):
        d.seq_scaling_list_present_flag[i] = bs.read_bits(1)
        if d.seq_scaling_list_present_flag[i]:
            if i < 6:
                scaling_list(
                    d.ScalingList4x4[i], bs, d.UseDefaultScalingMatrix4x4Flag, i)
            else:
                scaling_list(
                    d.ScalingList8x8[i-6], bs, d.UseDefaultScalingMatrix8x8Flag, i-6)


def seq_parameter_set_data(d:Table, bs:BitStream):
    d.add_field('profile_idc', bs.read_bits, count=8)
    d.add_field('constraint_set0_flag', bs.read_bits, count=1)
    d.add_field('constraint_set1_flag', bs.read_bits, count=1)
    d.add_field('constraint_set2_flag', bs.read_bits, count=1)
    d.add_field('constraint_set3_flag', bs.read_bits, count=1)
    d.add_field('constraint_set4_flag', bs.read_bits, count=1)
    d.add_field('constraint_set5_flag', bs.read_bits, count=1)
    bs.to_byte_end()  # reserved_zero_2bits
    d.add_field('level_idc', bs.read_bits, count=8)
    d.add_field('seq_parameter_set_id', bs.read_ue_golomb)
    if d.profile_idc in [100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135]:
        d.add_field('chroma_format_idc', bs.read_ue_golomb)
        if d.chroma_format_idc == 3:
            d.add_field('separate_colour_plane_flag', bs.read_bits, count=1)
        d.add_field('bit_depth_luma_minus8', bs.read_ue_golomb)
        d.add_field('bit_depth_chroma_minus', bs.read_ue_golomb)
        d.add_field('qpprime_y_zero_transform_bypass_flag',
                    bs.read_bits, count=1)
        d.add_field('seq_scaling_matrix_present_flag', bs.read_bits, count=1)
        if d.seq_scaling_matrix_present_flag:  # todo test this branch
            d.add_fields(__fields_in_scaling_list, 'seq_scaling_list_present_flag', 'ScalingList4x4',
                         'UseDefaultScalingMatrix4x4Flag', 'ScalingList8x8', 'UseDefaultScalingMatrix8x8Flag')
    d.add_field('log2_max_frame_num_minus4', bs.read_ue_golomb)
    d.add_field('pic_order_cnt_type', bs.read_ue_golomb)
    if d.pic_order_cnt_type == 0:
        d.add_field('log2_max_pic_order_cnt_lsb_minus4', bs.read_ue_golomb)
    elif d.pic_order_cnt_type == 1:
        d.add_field('delta_pic_order_always_zero_flag', bs.read_bits, count=1)
        d.add_field('offset_for_non_ref_pic', bs.read_se_golomb)
        d.add_field('offset_for_top_to_bottom_field', bs.read_se_golomb)
        d.add_field('num_ref_frames_in_pic_order_cnt_cycle', bs.read_ue_golomb)
        d.add_field('offset_for_ref_fram', bs.read_se_golombs,
                    count=d.num_ref_frames_in_pic_order_cnt_cycle)
    d.add_field('max_num_ref_frames', bs.read_ue_golomb)
    d.add_field('gaps_in_frame_num_value_allowed_flag', bs.read_bits, count=1)
    d.add_field('pic_width_in_mbs_minus1', bs.read_ue_golomb)
    d.add_field('pic_height_in_map_units_minus1', bs.read_ue_golomb)
    d.add_field('frame_mbs_only_flag',  bs.read_bits, count=1)
    if d.frame_mbs_only_flag == 0:
        d.add_field('mb_adaptive_frame_field_flag', bs.read_bits, count=1)
    d.add_field('direct_8x8_inference_flag', bs.read_bits, count=1)
    d.add_field('frame_cropping_flag', bs.read_bits, count=1)
    if d.frame_cropping_flag == 1:
        d.add_field('frame_crop_left_offset', bs.read_ue_golomb)
        d.add_field('frame_crop_right_offset', bs.read_ue_golomb)
        d.add_field('frame_crop_top_offset', bs.read_ue_golomb)
        d.add_field('frame_crop_bottom_offset', bs.read_ue_golomb)
    d.add_field('vui_parameters_present_flag', bs.read_bits, count=1)
    if d.vui_parameters_present_flag:
        d.add_table(vui_parameters)


def seq_parameter_set_rbsp(d:Table, bs:BitStream):
    d.add_table(seq_parameter_set_data)
    rbsp_trailing_bits(d,bs)


def seq_parameter_set_svc_extension(d:Table, bs:BitStream):
    pass


def svc_vui_parameters_extension(d:Table, bs:BitStream):
    pass


def seq_parameter_set_mvc_extension(d:Table, bs:BitStream):

    pass


def mvc_vui_parameters_extension(d:Table, bs:BitStream):
    pass


def seq_parameter_set_mvcd_extension(d:Table, bs:BitStream):
    pass


def seq_parameter_set_3davc_extension(d:Table, bs:BitStream):
    pass


def subset_seq_parameter_set_rbsp(d:Table, bs:BitStream):
    d.add_table(seq_parameter_set_data)
    # rbsp_trailing_bits(d,bs)


#=============================================================
# 以下是在H264标准基础上，根据自己的需求定义的处理过程
# 为了方便区分，均以analyse_开头定义（这不是强制的）
# 一般分析函数都会被循环调用，所以要保证每次调用分析函数时流位置刚好在包头，或者可以自动定位到包头
#=============================================================
def analyse_nalu_header(d:Table, bs:BitStream):
    find_start_code(bs)
    d.add_table(nal_unit)

def default_parser(d:Table, bs:BitStream):
    analyse_nalu_header(d, bs)
    rbsp_bs = BitStream(d.nal_unit.rbsp)

    d.context.add_exist(d.nal_unit)

    if d.nal_unit.nal_unit_type == 9:
        d.add_table(access_unit_delimiter_rbsp, bs=rbsp_bs)
    elif d.nal_unit.nal_unit_type == 6:
        d.add_table(sei_rbsp, bs=rbsp_bs)
    elif d.nal_unit.nal_unit_type in [1, 5]:
        d.add_table(slice_layer_without_partitioning_rbsp, bs=rbsp_bs)
    elif d.nal_unit.nal_unit_type == 7:
        d.add_table(seq_parameter_set_rbsp, bs=rbsp_bs)
    elif d.nal_unit.nal_unit_type == 8:
        d.add_table(pic_parameter_set_rbsp, bs=rbsp_bs)
    elif d.nal_unit.nal_unit_type == 15:
        d.add_table(subset_seq_parameter_set_rbsp, bs=rbsp_bs)
    elif d.nal_unit.nal_unit_type == 20:
        d.add_table(slice_layer_extension_rbsp, bs=rbsp_bs)


def analyse_slice_header(d:Table, bs:BitStream):
    analyse_nalu_header(d, bs)
    type = d.nal_unit.nal_unit_type
    if type in [1,5,20]:
        d.context.add_exist(d.nal_unit)
        d.add_table(slice_header, BitStream(d.nal_unit.rbsp))