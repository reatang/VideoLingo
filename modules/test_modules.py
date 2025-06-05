"""
# ----------------------------------------------------------------------------
# 模块测试脚本 - 验证重构后的原子模块功能
# ----------------------------------------------------------------------------
"""

import sys
import os
from pathlib import Path

# 添加modules目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from video_downloader import VideoDownloader
from audio_transcriber import AudioTranscriber


def test_video_downloader():
    """测试视频下载器模块"""
    print("=" * 60)
    print("🧪 测试视频下载器模块")
    print("=" * 60)
    
    try:
        # 创建下载器实例
        downloader = VideoDownloader(
            save_path='test_output',
            allowed_formats=['mp4', 'avi', 'mkv', 'mov', 'flv', 'webm']
        )
        
        # 测试获取视频信息功能
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # 示例URL
        print(f"📋 测试获取视频信息: {test_url}")
        
        info = downloader.get_video_info(test_url)
        if info:
            print(f"✅ 视频信息获取成功")
            print(f"  📺 标题: {info.get('title', '未知')}")
            print(f"  ⏱️  时长: {info.get('duration', 0)}秒")
            print(f"  👤 上传者: {info.get('uploader', '未知')}")
        else:
            print("⚠️  视频信息获取失败")
        
        print("\n✅ 视频下载器模块测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 视频下载器测试失败: {str(e)}")
        return False


def test_audio_transcriber():
    """测试音频转录器模块"""
    print("=" * 60)
    print("🧪 测试音频转录器模块")
    print("=" * 60)
    
    try:
        # 创建转录器实例
        transcriber = AudioTranscriber(
            output_dir='test_output',
            audio_dir='test_output/audio'
        )
        
        print("✅ 音频转录器实例创建成功")
        print(f"  📁 输出目录: {transcriber.output_dir}")
        print(f"  🎵 音频目录: {transcriber.audio_dir}")
        print(f"  ⏱️  目标分段长度: {transcriber.target_segment_length}秒")
        
        # 测试目录创建
        assert transcriber.output_dir.exists(), "输出目录创建失败"
        assert transcriber.audio_dir.exists(), "音频目录创建失败"
        assert (transcriber.output_dir / 'log').exists(), "日志目录创建失败"
        
        print("✅ 目录结构创建成功")
        
        # 测试文件名清理功能（通过创建模拟音频片段）
        import pandas as pd
        
        # 创建模拟转录结果
        mock_result = {
            'segments': [
                {
                    'speaker_id': None,
                    'words': [
                        {'word': ' Hello', 'start': 0.0, 'end': 0.5},
                        {'word': ' world', 'start': 0.5, 'end': 1.0},
                        {'word': '!', 'start': 1.0, 'end': 1.2}
                    ]
                }
            ]
        }
        
        # 测试转录结果处理
        df = transcriber.process_transcription_result(mock_result)
        print(f"✅ 转录结果处理测试成功，共{len(df)}条记录")
        
        # 测试保存功能
        output_file = transcriber.save_transcription_results(df)
        print(f"✅ 转录结果保存测试成功: {output_file}")
        
        print("\n✅ 音频转录器模块测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 音频转录器测试失败: {str(e)}")
        return False


def test_module_interfaces():
    """测试模块接口的一致性"""
    print("=" * 60)
    print("🧪 测试模块接口一致性")
    print("=" * 60)
    
    try:
        # 测试模块可以正常导入
        downloader = VideoDownloader()
        transcriber = AudioTranscriber()
        
        # 测试模块具有预期的方法
        downloader_methods = [
            'download_video', 'get_video_info', 'find_video_file'
        ]
        
        transcriber_methods = [
            'convert_video_to_audio', 'split_audio_by_silence', 
            'process_transcription_result', 'save_transcription_results'
        ]
        
        # 检查方法存在性
        for method in downloader_methods:
            assert hasattr(downloader, method), f"VideoDownloader缺少方法: {method}"
        
        for method in transcriber_methods:
            assert hasattr(transcriber, method), f"AudioTranscriber缺少方法: {method}"
        
        print("✅ 所有必需的方法都存在")
        
        # 测试输入输出类型提示
        import inspect
        
        # 检查关键方法的类型提示
        download_sig = inspect.signature(downloader.download_video)
        assert 'url' in download_sig.parameters, "download_video缺少url参数"
        assert download_sig.return_annotation == str, "download_video返回类型不正确"
        
        convert_sig = inspect.signature(transcriber.convert_video_to_audio)
        assert 'video_file' in convert_sig.parameters, "convert_video_to_audio缺少video_file参数"
        assert convert_sig.return_annotation == str, "convert_video_to_audio返回类型不正确"
        
        print("✅ 方法签名和类型提示正确")
        
        print("\n✅ 模块接口一致性测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 接口一致性测试失败: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始模块测试...")
    print()
    
    test_results = []
    
    # 运行各项测试
    test_results.append(("视频下载器模块", test_video_downloader()))
    test_results.append(("音频转录器模块", test_audio_transcriber()))
    test_results.append(("模块接口一致性", test_module_interfaces()))
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 测试统计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试都通过了！模块重构成功")
        return True
    else:
        print("💥 部分测试失败，需要修复问题")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 