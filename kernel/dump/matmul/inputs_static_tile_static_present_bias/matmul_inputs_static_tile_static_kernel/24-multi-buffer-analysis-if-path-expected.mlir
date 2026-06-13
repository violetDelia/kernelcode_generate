multi-buffer-analysis{memory_stage=2 fold=true target="npu_demo"}
#C166 = #symbol.expr<166>
#C206 = #symbol.expr<206>
#C1 = #symbol.expr<1>
#C241 = #symbol.expr<241>
#C0 = #symbol.expr<0>
#C48 = #symbol.expr<48>
#C80 = #symbol.expr<80>
#C56 = #symbol.expr<56>
#S_pattern_id = #symbol.expr<pattern_id>
#S_Q = #symbol.expr<?>
#S1 = #symbol.expr<166 - iter<0,166,48>>
#S2 = #symbol.expr<min(48, 166 - iter<0,166,48>)>
#S3 = #symbol.expr<241*iter<0,166,48>>
#S4 = #symbol.expr<206 - iter<0,206,80>>
#S5 = #symbol.expr<min(80, 206 - iter<0,206,80>)>
#S6 = #symbol.expr<241 - iter<0,241,56>>
#S7 = #symbol.expr<min(56, 241 - iter<0,241,56>)>
#S8 = #symbol.expr<241*iter<0,166,48> + iter<0,241,56>>
#S9 = #symbol.expr<206*iter<0,241,56>>
#S10 = #symbol.expr<206*iter<0,241,56> + iter<0,206,80>>
#It1 = #symbol.iter<start = #C0, end = #C166, step = #C48>
#It2 = #symbol.iter<start = #C0, end = #C206, step = #C80>
#It3 = #symbol.iter<start = #C0, end = #C241, step = #C56>

builtin.module {
  func.func @matmul_inputs_static_tile_static_kernel(%0: !nn.memory<[#C166, #C206], [#C206, #C1], f32, #nn.space<global>>, %1: !nn.memory<[#C166, #C241], [#C241, #C1], f32, #nn.space<global>>, %2: !nn.memory<[#C241, #C206], [#C206, #C1], f32, #nn.space<global>>, %3: !nn.memory<[#C206], [#C1], f32, #nn.space<global>>) attributes {entry_point} {
    %4 = tuner.select {patterns = [@matmul_inputs_static_tile_static_kernel_pattern0, @matmul_inputs_static_tile_static_kernel_pattern1]} : !symbol.int<#S_pattern_id>
    %5 = "symbol.const"() {value = #builtin.int<0>} : () -> !symbol.int<#C0>
    %6 = "symbol.eq"(%4, %5) : (!symbol.int<#S_pattern_id>, !symbol.int<#C0>) -> i1
    scf.if %6 {
      tuner.launch(@matmul_inputs_static_tile_static_kernel_pattern0, %0, %1, %2, %3) : (!nn.memory<[#C166, #C206], [#C206, #C1], f32, #nn.space<global>>, !nn.memory<[#C166, #C241], [#C241, #C1], f32, #nn.space<global>>, !nn.memory<[#C241, #C206], [#C206, #C1], f32, #nn.space<global>>, !nn.memory<[#C206], [#C1], f32, #nn.space<global>>) -> ()
    } else {
      tuner.launch(@matmul_inputs_static_tile_static_kernel_pattern1, %0, %1, %2, %3) : (!nn.memory<[#C166, #C206], [#C206, #C1], f32, #nn.space<global>>, !nn.memory<[#C166, #C241], [#C241, #C1], f32, #nn.space<global>>, !nn.memory<[#C241, #C206], [#C206, #C1], f32, #nn.space<global>>, !nn.memory<[#C206], [#C1], f32, #nn.space<global>>) -> ()
    } {analysis.if_id = "if1-1"}
    func.return
  }
  func.func @matmul_inputs_static_tile_static_kernel_pattern0(%0: !nn.memory<[#C166, #C206], [#C206, #C1], f32, #nn.space<global>>, %1: !nn.memory<[#C166, #C241], [#C241, #C1], f32, #nn.space<global>>, %2: !nn.memory<[#C241, #C206], [#C206, #C1], f32, #nn.space<global>>, %3: !nn.memory<[#C206], [#C1], f32, #nn.space<global>>) attributes {kernel.pattern_id = #builtin.int<0>} {
    %4 = symbol.const 166 : !symbol.int<#C166>
    %5 = symbol.const 241 : !symbol.int<#C241>
    %6 = symbol.const 206 : !symbol.int<#C206>
    %7 = symbol.const 0 : !symbol.int<#C0>
    %8 = symbol.const 48 : !symbol.int<#C48>
    %9 = symbol.const 80 : !symbol.int<#C80>
    %10 = symbol.const 1 : !symbol.int<#C1>
    // %11 raw analysis:
    // update point = loop2-2.
    // raw use domains = loop2-2 (%29 alias and output dma.deslice), loop3-3 (kernel.matmul acc), if2-2 (kernel.binary_elewise bias add).
    // num = 2 because update depth 2 is not the max depth 3 in the update/use point set.
    // advance is still scheduled in loop2-2; if2-2 and loop3-3 use the loop2-2 current slot.
    // multi_buffer.use_points keeps the full raw use domain list.
    %11 = "dma.alloc"(%8, %9) <{operandSegmentSizes = array<i32: 2>}> {multi_buffer.update_points = ["loop2-2"], multi_buffer.use_points = ["loop2-2", "loop3-3", "if2-2"], multi_buffer.num = "2"} : (!symbol.int<#C48>, !symbol.int<#C80>) -> !nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>
    %12 = "dma.alloc"(%9) <{operandSegmentSizes = array<i32: 1>}> {multi_buffer.update_points = ["loop2-2"], multi_buffer.use_points = ["loop2-2", "if2-2"], multi_buffer.num = "2"} : (!symbol.int<#C80>) -> !nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>
    %13 = "dma.alloc"(%8, %9) <{operandSegmentSizes = array<i32: 2>}> {multi_buffer.update_points = ["loop2-2"], multi_buffer.use_points = ["loop2-2", "if2-2"], multi_buffer.num = "2"} : (!symbol.int<#C48>, !symbol.int<#C80>) -> !nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>
    %14 = symbol.const 56 : !symbol.int<#C56>
    %15 = "dma.alloc"(%8, %14) <{operandSegmentSizes = array<i32: 2>}> {multi_buffer.update_points = ["loop3-3"], multi_buffer.use_points = ["loop3-3"], multi_buffer.num = "auto"} : (!symbol.int<#C48>, !symbol.int<#C56>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>
    %16 = "dma.alloc"(%14, %9) <{operandSegmentSizes = array<i32: 2>}> {multi_buffer.update_points = ["loop3-3"], multi_buffer.use_points = ["loop3-3"], multi_buffer.num = "auto"} : (!symbol.int<#C56>, !symbol.int<#C80>) -> !nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>
    %17 = memory.get_data %3 : !nn.memory<[#C206], [#C1], f32, #nn.space<global>> -> !symbol.ptr<f32>
    %18 = symbol.cast %17 : !symbol.ptr<f32> -> !symbol.int<#S_Q>
    %19 = symbol.ne %18, %7 : !symbol.int<#S_Q>, !symbol.int<#C0> -> i1
    %20 = "dma.alloc"(%8, %14) <{operandSegmentSizes = array<i32: 2>}> {multi_buffer.update_points = ["loop3-3"], multi_buffer.use_points = ["loop3-3"], multi_buffer.num = "auto"} : (!symbol.int<#C48>, !symbol.int<#C56>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>
    %21 = "dma.alloc"(%14, %9) <{operandSegmentSizes = array<i32: 2>}> {multi_buffer.update_points = ["loop3-3"], multi_buffer.use_points = ["loop3-3"], multi_buffer.num = "auto"} : (!symbol.int<#C56>, !symbol.int<#C80>) -> !nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm2>>
    symbol.for %22 = %7 to %4 step %8 {iter = #It1, analysis.loop_id = "loop1-1"} {
      %23 = symbol.sub %4, %22 : !symbol.int<#C166>, !symbol.iter<start = #C0, end = #C166, step = #C48> -> !symbol.int<#S1>
      %24 = symbol.min %8, %23 : !symbol.int<#C48>, !symbol.int<#S1> -> !symbol.int<#S2>
      %25 = symbol.mul %22, %5 : !symbol.iter<start = #C0, end = #C166, step = #C48>, !symbol.int<#C241> -> !symbol.int<#S3>
      symbol.for %26 = %7 to %6 step %9 {iter = #It2, analysis.loop_id = "loop2-2"} {
        %27 = symbol.sub %6, %26 : !symbol.int<#C206>, !symbol.iter<start = #C0, end = #C206, step = #C80> -> !symbol.int<#S4>
        %28 = symbol.min %9, %27 : !symbol.int<#C80>, !symbol.int<#S4> -> !symbol.int<#S5>
        %29 = "dma.reinterpret"(%11, %7, %24, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>
        %30 = "dma.reinterpret"(%12, %7, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 1, 1>}> : (!nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S5], [#C1], f32, #nn.space<tsm>>
        %31 = "dma.reinterpret"(%13, %7, %24, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>
        symbol.for %32 = %7 to %5 step %14 {iter = #It3, analysis.loop_id = "loop3-3"} {
          %33 = symbol.sub %5, %32 : !symbol.int<#C241>, !symbol.iter<start = #C0, end = #C241, step = #C56> -> !symbol.int<#S6>
          %34 = symbol.min %14, %33 : !symbol.int<#C56>, !symbol.int<#S6> -> !symbol.int<#S7>
          %35 = "dma.reinterpret"(%15, %7, %24, %34, %34, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#S7>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>
          %36 = "dma.reinterpret"(%16, %7, %34, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>
          %37 = symbol.add %25, %32 : !symbol.int<#S3>, !symbol.iter<start = #C0, end = #C241, step = #C56> -> !symbol.int<#S8>
          %38 = "dma.reinterpret"(%1, %37, %24, %34, %5, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C166, #C241], [#C241, #C1], f32, #nn.space<global>>, !symbol.int<#S8>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#C241>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#C241, #C1], f32, #nn.space<global>>
          %39 = symbol.mul %32, %6 : !symbol.iter<start = #C0, end = #C241, step = #C56>, !symbol.int<#C206> -> !symbol.int<#S9>
          %40 = symbol.add %39, %26 : !symbol.int<#S9>, !symbol.iter<start = #C0, end = #C206, step = #C80> -> !symbol.int<#S10>
          %41 = "dma.reinterpret"(%2, %40, %34, %28, %6, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C241, #C206], [#C206, #C1], f32, #nn.space<global>>, !symbol.int<#S10>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#C206>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#C206, #C1], f32, #nn.space<global>>
          "dma.deslice"(%35, %38, %7, %7, %24, %34, %10, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S7], [#C241, #C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
          "dma.deslice"(%36, %41, %7, %7, %34, %28, %10, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S7, #S5], [#C206, #C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
          %42 = "dma.reinterpret"(%20, %7, %24, %34, %34, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#S7>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>
          "dma.copy"(%42, %35) : (!nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>, !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>) -> ()
          %43 = "dma.reinterpret"(%21, %7, %34, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm2>>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm2>>
          "dma.copy"(%43, %36) : (!nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm2>>, !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()
          %acc = symbol.ne %32, %7 : !symbol.iter<start = #C0, end = #C241, step = #C56>, !symbol.int<#C0> -> i1
          "kernel.matmul"(%29, %42, %43, %acc) {space = #nn.space<tsm>} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>, !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm2>>, i1) -> ()
}
        scf.if %19 {
          %44 = "dma.reinterpret"(%3, %26, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 1, 1>}> : (!nn.memory<[#C206], [#C1], f32, #nn.space<global>>, !symbol.iter<start = #C0, end = #C206, step = #C80>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S5], [#C1], f32, #nn.space<global>>
          %45 = "dma.reinterpret"(%12, %7, %10, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#C1>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#C1, #S5], [#S5, #C1], f32, #nn.space<tsm>>
          "dma.deslice"(%30, %44, %7, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1>}> : (!nn.memory<[#S5], [#C1], f32, #nn.space<tsm>>, !nn.memory<[#S5], [#C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#S5>, !symbol.int<#C1>) -> ()
          "dma.broadcast"(%31, %45) {tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]], tile.tile_exprs = [["", ""], ["", ""]]} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#C1, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()
          "kernel.binary_elewise"(%29, %29, %31) {kind = "add", space = #nn.space<tsm>, tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]], tile.tile_exprs = [["", ""], ["", ""], ["", ""]]} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()
        } {analysis.if_id = "if2-2"}
        "dma.deslice"(%0, %29, %22, %26, %24, %28, %10, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#C166, #C206], [#C206, #C1], f32, #nn.space<global>>, !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !symbol.iter<start = #C0, end = #C166, step = #C48>, !symbol.iter<start = #C0, end = #C206, step = #C80>, !symbol.int<#S2>, !symbol.int<#S5>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
}
}
    "dma.free"(%21) : (!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm2>>) -> ()
    "dma.free"(%20) : (!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>) -> ()
    "dma.free"(%16) : (!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>) -> ()
    "dma.free"(%15) : (!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>) -> ()
    "dma.free"(%13) : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>) -> ()
    "dma.free"(%12) : (!nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>) -> ()
    "dma.free"(%11) : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>) -> ()
    func.return
  }
  func.func @matmul_inputs_static_tile_static_kernel_pattern1(%0: !nn.memory<[#C166, #C206], [#C206, #C1], f32, #nn.space<global>>, %1: !nn.memory<[#C166, #C241], [#C241, #C1], f32, #nn.space<global>>, %2: !nn.memory<[#C241, #C206], [#C206, #C1], f32, #nn.space<global>>, %3: !nn.memory<[#C206], [#C1], f32, #nn.space<global>>) attributes {kernel.pattern_id = #builtin.int<1>} {
    %4 = symbol.const 166 : !symbol.int<#C166>
    %5 = symbol.const 241 : !symbol.int<#C241>
    %6 = symbol.const 206 : !symbol.int<#C206>
    %7 = symbol.const 0 : !symbol.int<#C0>
    %8 = symbol.const 48 : !symbol.int<#C48>
    %9 = symbol.const 80 : !symbol.int<#C80>
    %10 = symbol.const 1 : !symbol.int<#C1>
    // %11 raw analysis:
    // update point = loop5-2.
    // raw use domains = loop5-2 (%29 alias and output dma.deslice), loop6-3 (kernel.matmul acc), if3-2 (kernel.binary_elewise bias add).
    // num = 2 because update depth 2 is not the max depth 3 in the update/use point set.
    // advance is still scheduled in loop5-2; if3-2 and loop6-3 use the loop5-2 current slot.
    // multi_buffer.use_points keeps the full raw use domain list.
    %11 = "dma.alloc"(%8, %9) <{operandSegmentSizes = array<i32: 2>}> {multi_buffer.update_points = ["loop5-2"], multi_buffer.use_points = ["loop5-2", "loop6-3", "if3-2"], multi_buffer.num = "2"} : (!symbol.int<#C48>, !symbol.int<#C80>) -> !nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>
    %12 = "dma.alloc"(%9) <{operandSegmentSizes = array<i32: 1>}> {multi_buffer.update_points = ["loop5-2"], multi_buffer.use_points = ["loop5-2", "if3-2"], multi_buffer.num = "2"} : (!symbol.int<#C80>) -> !nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>
    %13 = "dma.alloc"(%8, %9) <{operandSegmentSizes = array<i32: 2>}> {multi_buffer.update_points = ["loop5-2"], multi_buffer.use_points = ["loop5-2", "if3-2"], multi_buffer.num = "2"} : (!symbol.int<#C48>, !symbol.int<#C80>) -> !nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>
    %14 = symbol.const 56 : !symbol.int<#C56>
    %15 = "dma.alloc"(%8, %14) <{operandSegmentSizes = array<i32: 2>}> {multi_buffer.update_points = ["loop6-3"], multi_buffer.use_points = ["loop6-3"], multi_buffer.num = "auto"} : (!symbol.int<#C48>, !symbol.int<#C56>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>
    %16 = "dma.alloc"(%14, %9) <{operandSegmentSizes = array<i32: 2>}> {multi_buffer.update_points = ["loop6-3"], multi_buffer.use_points = ["loop6-3"], multi_buffer.num = "auto"} : (!symbol.int<#C56>, !symbol.int<#C80>) -> !nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>
    %17 = memory.get_data %3 : !nn.memory<[#C206], [#C1], f32, #nn.space<global>> -> !symbol.ptr<f32>
    %18 = symbol.cast %17 : !symbol.ptr<f32> -> !symbol.int<#S_Q>
    %19 = symbol.ne %18, %7 : !symbol.int<#S_Q>, !symbol.int<#C0> -> i1
    %20 = "dma.alloc"(%8, %14) <{operandSegmentSizes = array<i32: 2>}> {multi_buffer.update_points = ["loop6-3"], multi_buffer.use_points = ["loop6-3"], multi_buffer.num = "auto"} : (!symbol.int<#C48>, !symbol.int<#C56>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm2>>
    %21 = "dma.alloc"(%14, %9) <{operandSegmentSizes = array<i32: 2>}> {multi_buffer.update_points = ["loop6-3"], multi_buffer.use_points = ["loop6-3"], multi_buffer.num = "auto"} : (!symbol.int<#C56>, !symbol.int<#C80>) -> !nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm1>>
    symbol.for %22 = %7 to %4 step %8 {iter = #It1, analysis.loop_id = "loop4-1"} {
      %23 = symbol.sub %4, %22 : !symbol.int<#C166>, !symbol.iter<start = #C0, end = #C166, step = #C48> -> !symbol.int<#S1>
      %24 = symbol.min %8, %23 : !symbol.int<#C48>, !symbol.int<#S1> -> !symbol.int<#S2>
      %25 = symbol.mul %22, %5 : !symbol.iter<start = #C0, end = #C166, step = #C48>, !symbol.int<#C241> -> !symbol.int<#S3>
      symbol.for %26 = %7 to %6 step %9 {iter = #It2, analysis.loop_id = "loop5-2"} {
        %27 = symbol.sub %6, %26 : !symbol.int<#C206>, !symbol.iter<start = #C0, end = #C206, step = #C80> -> !symbol.int<#S4>
        %28 = symbol.min %9, %27 : !symbol.int<#C80>, !symbol.int<#S4> -> !symbol.int<#S5>
        %29 = "dma.reinterpret"(%11, %7, %24, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>
        %30 = "dma.reinterpret"(%12, %7, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 1, 1>}> : (!nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S5], [#C1], f32, #nn.space<tsm>>
        %31 = "dma.reinterpret"(%13, %7, %24, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>
        symbol.for %32 = %7 to %5 step %14 {iter = #It3, analysis.loop_id = "loop6-3"} {
          %33 = symbol.sub %5, %32 : !symbol.int<#C241>, !symbol.iter<start = #C0, end = #C241, step = #C56> -> !symbol.int<#S6>
          %34 = symbol.min %14, %33 : !symbol.int<#C56>, !symbol.int<#S6> -> !symbol.int<#S7>
          %35 = "dma.reinterpret"(%15, %7, %24, %34, %34, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#S7>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>
          %36 = "dma.reinterpret"(%16, %7, %34, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>
          %37 = symbol.add %25, %32 : !symbol.int<#S3>, !symbol.iter<start = #C0, end = #C241, step = #C56> -> !symbol.int<#S8>
          %38 = "dma.reinterpret"(%1, %37, %24, %34, %5, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C166, #C241], [#C241, #C1], f32, #nn.space<global>>, !symbol.int<#S8>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#C241>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#C241, #C1], f32, #nn.space<global>>
          %39 = symbol.mul %32, %6 : !symbol.iter<start = #C0, end = #C241, step = #C56>, !symbol.int<#C206> -> !symbol.int<#S9>
          %40 = symbol.add %39, %26 : !symbol.int<#S9>, !symbol.iter<start = #C0, end = #C206, step = #C80> -> !symbol.int<#S10>
          %41 = "dma.reinterpret"(%2, %40, %34, %28, %6, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C241, #C206], [#C206, #C1], f32, #nn.space<global>>, !symbol.int<#S10>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#C206>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#C206, #C1], f32, #nn.space<global>>
          "dma.deslice"(%35, %38, %7, %7, %24, %34, %10, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S7], [#C241, #C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
          "dma.deslice"(%36, %41, %7, %7, %34, %28, %10, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S7, #S5], [#C206, #C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
          %42 = "dma.reinterpret"(%20, %7, %24, %34, %34, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm2>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#S7>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm2>>
          "dma.copy"(%42, %35) : (!nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm2>>, !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>) -> ()
          %43 = "dma.reinterpret"(%21, %7, %34, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm1>>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm1>>
          "dma.copy"(%43, %36) : (!nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm1>>, !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()
          %acc = symbol.ne %32, %7 : !symbol.iter<start = #C0, end = #C241, step = #C56>, !symbol.int<#C0> -> i1
          "kernel.matmul"(%29, %42, %43, %acc) {space = #nn.space<tsm>} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm2>>, !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm1>>, i1) -> ()
}
        scf.if %19 {
          %44 = "dma.reinterpret"(%3, %26, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 1, 1>}> : (!nn.memory<[#C206], [#C1], f32, #nn.space<global>>, !symbol.iter<start = #C0, end = #C206, step = #C80>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S5], [#C1], f32, #nn.space<global>>
          %45 = "dma.reinterpret"(%12, %7, %10, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#C1>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#C1, #S5], [#S5, #C1], f32, #nn.space<tsm>>
          "dma.deslice"(%30, %44, %7, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1>}> : (!nn.memory<[#S5], [#C1], f32, #nn.space<tsm>>, !nn.memory<[#S5], [#C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#S5>, !symbol.int<#C1>) -> ()
          "dma.broadcast"(%31, %45) {tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]], tile.tile_exprs = [["", ""], ["", ""]]} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#C1, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()
          "kernel.binary_elewise"(%29, %29, %31) {kind = "add", space = #nn.space<tsm>, tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]], tile.tile_exprs = [["", ""], ["", ""], ["", ""]]} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()
        } {analysis.if_id = "if3-2"}
        "dma.deslice"(%0, %29, %22, %26, %24, %28, %10, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#C166, #C206], [#C206, #C1], f32, #nn.space<global>>, !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !symbol.iter<start = #C0, end = #C166, step = #C48>, !symbol.iter<start = #C0, end = #C206, step = #C80>, !symbol.int<#S2>, !symbol.int<#S5>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
}
}
    "dma.free"(%21) : (!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm1>>) -> ()
    "dma.free"(%20) : (!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm2>>) -> ()
    "dma.free"(%16) : (!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>) -> ()
    "dma.free"(%15) : (!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>) -> ()
    "dma.free"(%13) : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>) -> ()
    "dma.free"(%12) : (!nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>) -> ()
    "dma.free"(%11) : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>) -> ()
    func.return
  }
}
