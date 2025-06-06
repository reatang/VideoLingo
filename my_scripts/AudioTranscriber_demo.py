"""
# ----------------------------------------------------------------------------
# ASR引擎适配器演示程序
# 
# 演示如何使用重构后的AudioTranscriber模块进行完整的音频转录流程：
# 1. 视频转音频
# 2. 音频分段处理  
# 3. 选择ASR引擎进行转录
# 4. 结果处理和保存
# ----------------------------------------------------------------------------
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 分步导入以便更好地诊断问题
try:
    print("🔍 开始导入音频转录器模块...")
    
    # 先测试基础模块
    from modules.asr_backend.base import ASREngineBase, ASRResult
    print("✅ 基础模块导入成功")
    
    # 测试重构后的音频转录器模块
    from modules.audio_transcriber import AudioTranscriber
    print("✅ 音频转录器模块导入成功")
    
    # 测试工厂模块
    from modules.asr_backend.factory import (
        create_asr_engine, 
        cleanup_all_engines,
    )
    print("✅ 工厂模块导入成功")
    
    print("✅ 所有模块加载成功")
    
except ImportError as e:
    print(f"❌ 无法导入模块: {str(e)}")
    print("请确保模块已正确安装")
    print("\n🔧 尝试逐步诊断问题...")
    
    # 尝试逐步导入以找出具体问题
    try:
        import modules.audio_transcriber
        print("✅ 音频转录器主模块可以导入")
    except Exception as e2:
        print(f"❌ 音频转录器主模块导入失败: {e2}")
    
    try:
        from modules import audio_transcriber
        print("✅ 从modules导入成功")
    except Exception as e3:
        print(f"❌ 从modules导入失败: {e3}")
        
    sys.exit(1)
except Exception as e:
    print(f"❌ 其他导入错误: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def demonstrate_audio_processing():
    """演示完整的音频转录流程 - 一个函数搞定所有"""
    print("\n🎬 开始完整的音频转录演示...")
    
    # ========================================================================
    # 第一步：获取视频文件
    # ========================================================================
    if len(sys.argv) > 1:
        video_file = sys.argv[1]
    else:
        video_file = input("请输入视频文件路径: ").strip()
    
    if not video_file or not os.path.exists(video_file):
        print("❌ 视频文件不存在或路径为空")
        return
    
    print(f"📁 处理视频文件: {video_file}")
    
    # ========================================================================
    # 第二步：初始化音频转录器
    # ========================================================================
    print("\n🔧 初始化AudioTranscriber...")
    transcriber = AudioTranscriber(
        output_dir="my_scripts/output",
        audio_dir="my_scripts/output/audio",
        target_segment_length=30*60,  # 30分钟
        silence_window=60,           # 1分钟窗口
        target_db=-20.0
    )
    
    try:
        # ====================================================================
        # 第三步：视频转音频
        # ====================================================================
        print("\n🎬➡️🎵 步骤1: 视频转音频...")
        audio_file = transcriber.convert_video_to_audio(video_file)
        print(f"✅ 音频文件路径: {audio_file}")
        
        # ====================================================================
        # 第四步：获取音频信息
        # ====================================================================
        print("\n📏 步骤2: 获取音频信息...")
        duration = transcriber.get_audio_duration(audio_file)
        print(f"⏱️  音频时长: {duration:.1f}秒 ({duration/60:.1f}分钟)")
        
        # ====================================================================
        # 第五步：音频分段
        # ====================================================================
        print("\n✂️  步骤3: 智能音频分段...")
        segments = transcriber.split_audio_by_silence(audio_file)
        
        print(f"📊 分段完成: 共{len(segments)}个片段")
        for i, (start, end) in enumerate(segments):
            print(f"  片段{i+1}: {start:.1f}s - {end:.1f}s (时长: {end-start:.1f}s)")
        
        # ====================================================================
        # 第六步：选择转录方式
        # ====================================================================
        print(f"\n🤔 选择转录方式:")
        print("1. 单片段转录演示（推荐用于测试）")
        print("2. 一键完整转录（处理所有片段）")
        
        choice = input("请选择 (1/2, 默认1): ").strip()
        if choice == '2':
            # ================================================================
            # 方式2：一键完整转录
            # ================================================================
            print("\n🚀 方式2: 开始一键完整转录...")
            engine_type = "local"
            
            output_file = transcriber.transcribe_video_complete(
                video_file=video_file,
                use_vocal_separation=False,  # 简化演示，不使用人声分离
                engine_type=engine_type,
                config=None
            )
            
            print(f"✅ 一键转录完成！")
            print(f"📁 转录结果已保存: {output_file}")
            
        else:
            # ================================================================
            # 方式1：单片段转录演示
            # ================================================================
            print("\n🎤 方式1: 开始单片段转录演示...")
            
            # 选择要转录的片段
            if len(segments) > 1:
                print(f"\n📊 检测到{len(segments)}个音频片段")
                choice = input("是否只转录第一个片段? (y/n, 默认y): ").strip().lower()
                if choice == 'n':
                    selected_segments = segments
                else:
                    selected_segments = segments[:1]
            else:
                selected_segments = segments
            
            print(f"🎯 将转录{len(selected_segments)}个片段")
            
            # 设置转录引擎
            engine_type = "local"
            config = None
            
            # 逐个转录片段
            all_results = []
            
            for i, (start_time, end_time) in enumerate(selected_segments):
                print(f"\n🎤 转录片段{i+1}/{len(selected_segments)}: {start_time:.1f}s - {end_time:.1f}s")
                
                try:
                    # 使用AudioTranscriber的转录方法
                    result = transcriber.transcribe_audio_segment(
                        audio_file=audio_file,
                        vocal_audio_file=audio_file,  # 简化演示，使用同一文件
                        start_time=start_time,
                        end_time=end_time,
                        engine_type=engine_type,
                        config=config
                    )
                    
                    all_results.append(result)
                    
                    # 显示部分结果
                    if result.segments:
                        sample_text = result.segments[0].text[:100]
                        print(f"✅ 转录完成，检测语言: {result.language}")
                        print(f"📝 转录样例: {sample_text}...")
                    else:
                        print("⚠️  未检测到语音内容")
                    
                except Exception as e:
                    print(f"❌ 片段{i+1}转录失败: {str(e)}")
                    continue
            
            # ================================================================
            # 第七步：处理和保存转录结果
            # ================================================================
            if all_results:
                print(f"\n📊 转录总结:")
                total_segments = sum(len(r.segments) for r in all_results)
                total_words = sum(len(w.word) for r in all_results for seg in r.segments for w in seg.words)
                
                print(f"  总片段数: {len(selected_segments)}")
                print(f"  转录段落: {total_segments}")
                print(f"  识别词汇: {total_words}")
                
                # 保存结果
                if total_words > 0:
                    save_choice = input("\n💾 是否保存转录结果? (y/n, 默认y): ").strip().lower()
                    if save_choice != 'n':
                        print("💾 保存转录结果...")
                        
                        # 合并所有结果
                        all_words = []
                        for result in all_results:
                            result_df = result.to_dataframe()
                            if not result_df.empty:
                                all_words.append(result_df)
                        
                        if all_words:
                            import pandas as pd
                            combined_df = pd.concat(all_words, ignore_index=True)
                            
                            # 使用AudioTranscriber保存结果
                            saved_file = transcriber.save_transcription_results(combined_df)
                            
                            print(f"✅ 转录结果已保存: {saved_file}")
                            print(f"📈 数据统计: {len(combined_df)}条记录")
                        else:
                            print("⚠️  没有有效的转录结果可保存")
                else:
                    print("⚠️  未检测到有效的转录内容")
            else:
                print("⚠️  所有片段转录都失败了")
        
        print("\n🎉 演示完成！AudioTranscriber模块工作正常")
        
    except Exception as e:
        print(f"❌ 处理过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        print("\n🧹 清理资源...")
        cleanup_all_engines()


def main():
    """主函数"""
    print("🎬 AudioTranscriber完整演示程序")
    print("=" * 50)

    # 初始化配置模块
    try:
        from modules.config import get_config_manager
        config = get_config_manager()
        print("✅ 配置模块加载成功")
    except Exception as e:
        print(f"⚠️  配置模块加载失败: {e}")
    
    try:
        # 运行完整演示
        demonstrate_audio_processing()
        
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，演示结束")
    except Exception as e:
        print(f"\n💥 演示过程中发生错误: {str(e)}")
    finally:
        # 确保清理所有引擎资源
        print("\n🧹 最终清理...")
        cleanup_all_engines()
        print("✅ 演示程序结束")


if __name__ == "__main__":
    main()