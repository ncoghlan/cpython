/* Frame object interface */

// TODO: Rearrange this to follow the new include header layout

#ifndef Py_LIMITED_API
#ifndef Py_FRAMEOBJECT_H
#define Py_FRAMEOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int b_type;                 /* what kind of block this is */
    int b_handler;              /* where to jump to find handler */
    int b_level;                /* value stack level to pop to */
} PyTryBlock;

typedef struct _frame {
    PyObject_VAR_HEAD
    struct _frame *f_back;      /* previous frame, or NULL */
    PyCodeObject *f_code;       /* code segment */
    PyObject *f_builtins;       /* builtin symbol table (PyDictObject) */
    PyObject *f_globals;        /* global symbol table (PyDictObject) */
    PyObject *f_locals;         /* local symbol table (any mapping) */
    PyObject **f_valuestack;    /* points after the last local */
    /* Next free slot in f_valuestack.  Frame creation sets to f_valuestack.
       Frame evaluation usually NULLs it, but a frame that yields sets it
       to the current stack top. */
    PyObject **f_stacktop;
    PyObject *f_trace;          /* Trace function */
    char f_trace_lines;         /* Emit per-line trace events? */
    char f_trace_opcodes;       /* Emit per-opcode trace events? */

    /* Borrowed reference to a generator, or NULL */
    PyObject *f_gen;

    int f_lasti;                /* Last instruction if called */
    /* Call PyFrame_GetLineNumber() instead of reading this field
       directly.  As of 2.3 f_lineno is only valid when tracing is
       active (i.e. when f_trace is set).  At other times we use
       PyCode_Addr2Line to calculate the line from the current
       bytecode index. */
    int f_lineno;               /* Current line number */
    int f_iblock;               /* index in f_blockstack */
    char f_executing;           /* whether the frame is still executing */
    PyTryBlock f_blockstack[CO_MAXBLOCKS]; /* for try and loop blocks */
    PyObject *f_localsplus[1];  /* locals+stack, dynamically sized */
} PyFrameObject;


/* Standard object interface */

PyAPI_DATA(PyTypeObject) PyFrame_Type;

#define PyFrame_Check(op) (Py_TYPE(op) == &PyFrame_Type)

PyAPI_FUNC(PyFrameObject *) PyFrame_New(PyThreadState *, PyCodeObject *,
                                        PyObject *, PyObject *);

/* only internal use */
PyFrameObject* _PyFrame_New_NoTrack(PyThreadState *, PyCodeObject *,
                                    PyObject *, PyObject *);


/* The rest of the interface is specific for frame objects */

/* Block management functions */

PyAPI_FUNC(void) PyFrame_BlockSetup(PyFrameObject *, int, int, int);
PyAPI_FUNC(PyTryBlock *) PyFrame_BlockPop(PyFrameObject *);

/* Extend the value stack */

PyAPI_FUNC(PyObject **) PyFrame_ExtendStack(PyFrameObject *, int, int);

PyAPI_FUNC(int) PyFrame_ClearFreeList(void);

PyAPI_FUNC(void) _PyFrame_DebugMallocStats(FILE *out);

/* Return the line of code the frame is currently executing. */
PyAPI_FUNC(int) PyFrame_GetLineNumber(PyFrameObject *);


/* Conversions between "fast locals" and locals in dictionary */
PyAPI_FUNC(int) PyFrame_FastToLocalsWithError(PyFrameObject *f);
PyAPI_FUNC(void) PyFrame_FastToLocals(PyFrameObject *);

#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 >= 0x03080000
/* Fast locals proxy for reliable write-through from trace functions */
PyTypeObject PyFastLocalsProxy_Type;
#define _PyFastLocalsProxy_CheckExact(self) \
    (Py_TYPE(self) == &PyFastLocalsProxy_Type)

/* Access the frame locals mapping */
PyAPI_FUNC(PyObject *) PyFrame_GetPyLocals(PyFrameObject *); // = locals()
PyAPI_FUNC(PyObject *) PyFrame_GetLocalsAttr(PyFrameObject *);  // = frame.f_locals
#endif

#ifdef Py_BUILD_CORE
PyObject *_PyFrame_BorrowPyLocals(PyFrameObject *f); /* For PyEval_GetLocals() */
void _PyFrame_PostEvalCleanup(PyFrameObject *f);     /* For _PyEval_EvalFrame() */
#endif


/* This always raises RuntimeError now (use PyFrame_GetLocalsAttr() instead) */
PyAPI_FUNC(void) PyFrame_LocalsToFast(PyFrameObject *, int);

#ifdef __cplusplus
}
#endif
#endif /* !Py_FRAMEOBJECT_H */
#endif /* Py_LIMITED_API */
