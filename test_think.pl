
:- use_module(agi_core).
:- initialization(main, main).
main :-
    cathedral_v96:agi_init,
    trace,
    cathedral_v96:think('O que é um material topológico?', Output, Status1),
    writeln(Output), writeln(Status1).
