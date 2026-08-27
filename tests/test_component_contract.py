"""Static ownership and hot-path contracts for esp_video_camera."""

from pathlib import Path


COMPONENT = Path(__file__).resolve().parents[1] / "components" / "esp_video_camera"


def test_jpeg_quality_uses_extended_controls() -> None:
    source = (COMPONENT / "esp_video_camera.cpp").read_text()
    start = source.index("bool ESPVideoCamera::start_jpeg_pipeline_()")
    end = source.index("bool ESPVideoCamera::", start + 1)
    pipeline = source[start:end]

    assert 'this->jpeg_quality_, "jpeg_quality"' in pipeline
    assert "gate_set_ext_ctrl(" in pipeline
    assert "ioctl(this->jpeg_fd_, VIDIOC_S_CTRL" not in pipeline


def test_capture_worker_is_event_driven_and_reuses_owned_buffers() -> None:
    source = (COMPONENT / "esp_video_camera.cpp").read_text()
    header = (COMPONENT / "esp_video_camera.h").read_text()

    assert 'this->set_timeout("capture_linger", LINGER_MS' in source
    assert "this->enable_loop_soon_any_context();" in source
    assert "this->disable_loop();" in source
    capture_start = source[source.index("bool ESPVideoCamera::start_direct_capture_") :]
    assert "O_RDWR | O_NONBLOCK" not in capture_start
    hot_path = source[
        source.index("void ESPVideoCamera::capture_task_run_()") :
        source.index("void ESPVideoCamera::deliver_raw_frame_(")
    ]
    assert "vTaskDelay" not in hot_path
    assert "ulTaskNotifyTake(pdTRUE, portMAX_DELAY);" in source
    assert "MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT" in source
    assert "copy = (uint8_t *) heap_caps_malloc(length, MALLOC_CAP_8BIT)" not in source
    assert "std::atomic<uint8_t> references{2};" in source
    assert "release.count = 0;" in source
    assert "capture_prepared_" in header
    assert "capture_streaming_" in header


def test_capture_lifecycle_has_one_bounded_owner() -> None:
    source = (COMPONENT / "esp_video_camera.cpp").read_text()
    header = (COMPONENT / "esp_video_camera.h").read_text()

    assert "schedule_capture_retry_();" in source
    assert 'this->set_timeout("capture_retry", CAPTURE_RETRY_MS' in source
    assert "MAX_CAPTURE_RETRIES" in header
    assert "void on_shutdown() override;" in header
    assert "capture_task_running_" in header
    assert "capture_task_done_storage_" in header
    assert "CAPTURE_STOP_TIMEOUT_MS = 3000" in header
    assert "void ESPVideoCamera::on_shutdown()" in source
    assert "esp_video_deinit()" in source
    assert "Camera pipeline stopped cleanly" in source
    assert "bool ESPVideoCamera::resume_capture_()" in source
    assert "bool ESPVideoCamera::suspend_capture_()" in source
    assert "bool ESPVideoCamera::stop_capture_()" in source
    assert "Camera teardown deferred: V4L2 queue still active" in source
    assert "REQBUFS(0) failed" in source


def test_raw_consumer_and_ppa_contracts_remain_explicit() -> None:
    source = (COMPONENT / "esp_video_camera.cpp").read_text()
    header = (COMPONENT / "esp_video_camera.h").read_text()

    assert "RawVideoFrameConsumer" in header
    assert "register_raw_frame_consumer" in source
    assert "start_raw_frame_consumer" in source
    assert "stop_raw_frame_consumer" in source
    assert "ppa_do_scale_rotate_mirror" in source
    assert "this->ppa_transform_required_" in source
    assert "operation.scale_x = this->ppa_scale_x_;" in source
    assert "operation.scale_y = this->ppa_scale_y_;" in source
    assert "rotated_rgb565_capacity_" in header
    assert "V4L2_PIX_FMT_YUV420" in source
    assert "capture_pixel_format_" in source


def test_component_uses_current_esp_video_contract() -> None:
    config = (COMPONENT / "__init__.py").read_text()

    assert 'add_idf_component(name="espressif/esp_video", ref="2.4.1")' in config
    assert (
        '"CONFIG_ESP_VIDEO_ENABLE_HW_JPEG_ENC_VIDEO_DEVICE", jpeg_enabled'
        in config
    )
    assert "CONF_BUFFER_COUNT" in config
